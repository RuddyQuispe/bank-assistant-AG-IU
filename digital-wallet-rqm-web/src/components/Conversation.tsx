import { useEffect, useState } from 'react'
import { randomUUID, type ToolMessage } from '@ag-ui/client'
import { createWalletAgent } from '../api/agent'
import { toErrorMessage } from '../api/config'
import { getHistory } from '../api/sessions'
import { APPEARANCE_TOOLS, runToolCall } from '../tools/appearance-tools'
import { SCAN_QR_TOOL, scanResultMessage } from '../tools/scan-qr'
import { PAYMENT_PAUSE_EVENT, cancelPayment, confirmPayment, parsePaymentPause } from '../tools/qr-payment-resume'
import { parseBalanceCard } from '../display/balance-card'
import { parsePaymentReceipt } from '../display/payment-receipt'
import { parseQrPaymentCard, type QrPaymentCardData } from '../display/qr-payment-card'
import { DISPLAY_TOOLS, isDisplayTool, parseDisplayCard } from '../display/display-tools'
import type { ChatMessage } from '../models/chat/chat-message.model'
import { ChatPanel } from './ChatPanel'
import { ConfirmPaymentDialog } from './ConfirmPaymentDialog'
import type { PaymentChoice } from './QrPaymentCard'
import { QrScannerModal } from './QrScannerModal'

// Texto que ve el usuario por cada nodo del grafo del backend (stepName de AG-UI).
const STEP_LABELS: Record<string, string> = {
  ingest: 'Reading your question…',
  analyzer: 'Understanding what you need…',
  retrieve: 'Searching the knowledge base…',
  bank_tools: 'Checking your account…',
  interface: 'Updating the app…',
  qr_payment: 'Looking up the QR…',
  qr_confirm: 'Processing the payment…',
  interpreter: 'Writing the answer…',
}

const CARD_UNAVAILABLE = 'This card could not be displayed.'

// Tools que el navegador ejecuta (apariencia, escáner QR) y las que solo dibuja (tarjetas)
const CLIENT_TOOLS = [...APPEARANCE_TOOLS, SCAN_QR_TOOL, ...DISPLAY_TOOLS]

// Escaneo en curso: el agente espera el código que elija el usuario en el escáner
interface PendingScan {
  toolCallId: string
  resolve: (result: ToolMessage) => void
}

// Pago que el usuario está por confirmar en el diálogo
interface PaymentToConfirm {
  card: QrPaymentCardData
  choice: PaymentChoice
}

// Lo que dejó un run: resultados de tools del navegador, si el grafo quedó en pausa y si respondió con texto
interface RunOutcome {
  toolResults: ToolMessage[]
  pausedQr: string | null
  answered: boolean
}

interface ConversationProps {
  token: string
  sessionId: string
  onRunFinished: () => void
}

// Una sesión abierta: carga su historial, envía preguntas y muestra la respuesta en streaming.
// El padre la vuelve a montar (key) al cambiar de sesión, por eso todo arranca limpio.
export function Conversation({ token, sessionId, onRunFinished }: ConversationProps) {
  // El agente se crea una sola vez por sesión abierta.
  const [agent] = useState(() => createWalletAgent(token, sessionId))
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [running, setRunning] = useState(false)
  // Paso del agente en curso; se muestra mientras todavía no hay texto de respuesta.
  const [step, setStep] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [scan, setScan] = useState<PendingScan | null>(null)
  // Token del QR que el grafo espera pagar (quedó en pausa con interrupt)
  const [pendingQr, setPendingQr] = useState<string | null>(null)
  const [toConfirm, setToConfirm] = useState<PaymentToConfirm | null>(null)

  // 1. Al abrir: trae el historial y se lo da al agente para que tenga el contexto.
  useEffect(() => {
    async function loadHistory() {
      try {
        const history = await getHistory(token, sessionId)
        const loaded: ChatMessage[] = history.map((m) => ({
          id: randomUUID(),
          role: m.role === 'human' ? 'user' : 'assistant',
          content: m.content,
          // Tarjetas guardadas: se vuelven a dibujar con los mismos datos
          card: parseBalanceCard(m.card) ?? undefined,
          qrPayment: parseQrPaymentCard(m.qr_payment) ?? undefined,
          receipt: parsePaymentReceipt(m.receipt) ?? undefined,
        }))
        const hasCard = (m: ChatMessage) => Boolean(m.card || m.qrPayment || m.receipt)
        setMessages(loaded.map((m) => (hasCard(m) || m.content ? m : { ...m, content: CARD_UNAVAILABLE })))
        // Al agente solo le sirve el texto; las tarjetas ya están en el checkpoint del backend
        agent.setMessages(loaded.filter((m) => !hasCard(m) && m.content))
      } catch (err) {
        setError(toErrorMessage(err))
      } finally {
        setLoadingHistory(false)
      }
    }
    loadHistory()
  }, [agent, token, sessionId])

  // Ejecuta el agente una vez: cada evento AG-UI actualiza la pantalla apenas llega.
  // forwardedProps lleva la decisión del pago cuando el run reanuda un grafo en pausa.
  async function runOnce(forwardedProps?: Record<string, unknown>): Promise<RunOutcome> {
    // Algunas tools terminan al instante (apariencia) y otras esperan al usuario (escáner)
    const toolResults: Promise<ToolMessage>[] = []
    let pausedQr: string | null = null
    let answered = false
    await agent.runAgent(
      // El backend recibe qué tools tiene el navegador; si el agente pide una, llega como TOOL_CALL_*.
      { tools: CLIENT_TOOLS, forwardedProps },
      {
        // El backend entra a un nodo del grafo: se muestra qué está haciendo.
        onStepStartedEvent: ({ event }) => {
          setStep(STEP_LABELS[event.stepName] ?? 'Working…')
        },
        // Empieza la respuesta: burbuja vacía y ya no hace falta el paso.
        onTextMessageStartEvent: ({ event }) => {
          answered = true
          setStep(null)
          setMessages((current) => [...current, { id: event.messageId, role: 'assistant', content: '' }])
        },
        // Llega un pedazo: textMessageBuffer es el texto ANTERIOR, por eso se le suma el delta.
        onTextMessageContentEvent: ({ event, textMessageBuffer }) => {
          const text = textMessageBuffer + event.delta
          setMessages((current) => current.map((m) => (m.id === event.messageId ? { ...m, content: text } : m)))
        },
        onToolCallEndEvent: ({ event, toolCallName, toolCallArgs }) => {
          // Tool de solo mostrar (saldo, cobro QR, comprobante): se dibuja en el chat y no devuelve resultado
          if (isDisplayTool(toolCallName)) {
            const display = parseDisplayCard(toolCallName, toolCallArgs)
            // Datos rotos: se avisa en vez de dejar al usuario sin nada (el texto dice que hay una tarjeta)
            const content = display ? '' : CARD_UNAVAILABLE
            setMessages((current) => [...current, { id: event.toolCallId, role: 'assistant', content, ...display }])
            return
          }
          // El agente pidió escanear un QR: se abre el escáner y el resultado llega cuando el usuario elige
          if (toolCallName === SCAN_QR_TOOL.name) {
            const toolCallId = event.toolCallId
            toolResults.push(new Promise((resolve) => setScan({ toolCallId, resolve })))
            return
          }
          // El agente pidió una tool del navegador (tema, fondo, fuente): se aplica y se guarda su resultado.
          toolResults.push(Promise.resolve(runToolCall(event.toolCallId, toolCallName, toolCallArgs)))
        },
        // El grafo quedó en pausa esperando que el usuario confirme el pago del QR
        onCustomEvent: ({ event }) => {
          if (event.name === PAYMENT_PAUSE_EVENT) pausedQr = parsePaymentPause(event.value)
        },
        // El backend avisó un error dentro del stream.
        onRunErrorEvent: ({ event }) => {
          setError(event.message)
        },
      },
    )
    return { toolResults: await Promise.all(toolResults), pausedQr, answered }
  }

  // Un turno completo: el run y, si el navegador ejecutó tools, otro run con sus resultados.
  async function runTurn(forwardedProps?: Record<string, unknown>): Promise<RunOutcome> {
    let outcome = await runOnce(forwardedProps)
    // Avisa al padre para que refresque títulos y consumo (aunque falle la confirmación).
    onRunFinished()
    if (outcome.toolResults.length > 0) {
      // Ese run va directo al backend con los resultados; no pide más tools del navegador.
      outcome.toolResults.forEach((result) => agent.addMessage(result))
      try {
        outcome = await runOnce()
        onRunFinished()
      } catch (err) {
        // La acción ya quedó aplicada: solo falló el mensaje de confirmación
        setError(`The action was applied, but the confirmation failed: ${toErrorMessage(err)}`)
      }
    }
    // Si quedó en pausa, la tarjeta de ese QR habilita "Pay"; si no, ya no hay pago pendiente
    setPendingQr(outcome.pausedQr)
    return outcome
  }

  // Corre algo mostrando el estado de "enviando" y los errores de red o HTTP (401, 404...)
  async function withRunning(work: () => Promise<void>) {
    setRunning(true)
    setError(null)
    try {
      await work()
    } catch (err) {
      setError(toErrorMessage(err))
    } finally {
      setRunning(false)
      setStep(null)
    }
  }

  function handleSend(question: string) {
    const userMessage: ChatMessage = { id: randomUUID(), role: 'user', content: question }
    setMessages((current) => [...current, userMessage])
    return withRunning(async () => {
      // 2. Con un pago pendiente, el backend no procesa mensajes nuevos: primero se cancela el pago
      if (pendingQr) await runTurn(cancelPayment())
      agent.addMessage(userMessage)
      const outcome = await runTurn()
      // 3. Pausa que esta pestaña no conocía (por ejemplo, después de recargar): el mensaje no se procesó.
      //    Se cancela ese pago y se vuelve a enviar el mensaje.
      if (outcome.pausedQr && !outcome.answered) {
        await runTurn(cancelPayment())
        await runTurn()
      }
    })
  }

  // 4. "Confirm payment" o "Cancel" en el diálogo: reanuda el grafo con la decisión
  function finishPayment(confirmed: boolean) {
    if (!toConfirm) return
    const { choice } = toConfirm
    setToConfirm(null)
    const decision = confirmed ? confirmPayment(choice.account.accountNumber, choice.amount) : cancelPayment()
    return withRunning(async () => {
      await runTurn(decision)
    })
  }

  // Cierra el escáner y devuelve al agente el código elegido (o null si se canceló)
  function finishScan(code: string | null) {
    if (!scan) return
    scan.resolve(scanResultMessage(scan.toolCallId, code))
    setScan(null)
  }

  if (loadingHistory) {
    return (
      <div className="flex-grow-1 d-flex align-items-center justify-content-center">
        <span className="spinner-border text-primary" aria-label="Loading history" />
      </div>
    )
  }

  return (
    <>
      <ChatPanel
        messages={messages}
        running={running}
        step={step}
        error={error}
        onSend={handleSend}
        payableQr={pendingQr}
        onPayQr={(card, choice) => setToConfirm({ card, choice })}
      />
      {scan && <QrScannerModal token={token} onScan={(code) => finishScan(code)} onCancel={() => finishScan(null)} />}
      {toConfirm && (
        <ConfirmPaymentDialog
          card={toConfirm.card}
          choice={toConfirm.choice}
          onConfirm={() => finishPayment(true)}
          onCancel={() => finishPayment(false)}
        />
      )}
    </>
  )
}
