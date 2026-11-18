import { useEffect, useState } from 'react'
import { randomUUID, type ToolMessage } from '@ag-ui/client'
import { createWalletAgent } from '../api/agent'
import { toErrorMessage } from '../api/config'
import { getHistory } from '../api/sessions'
import { APPEARANCE_TOOLS, runToolCall } from '../tools/appearance-tools'
import { parseBalanceCard } from '../display/balance-card'
import { DISPLAY_TOOLS, isDisplayTool } from '../display/display-tools'
import type { ChatMessage } from '../models/chat/chat-message.model'
import { ChatPanel } from './ChatPanel'

// Texto que ve el usuario por cada nodo del grafo del backend (stepName de AG-UI).
const STEP_LABELS: Record<string, string> = {
  ingest: 'Reading your question…',
  analyzer: 'Understanding what you need…',
  retrieve: 'Searching the knowledge base…',
  bank_tools: 'Checking your account…',
  interface: 'Updating the app…',
  interpreter: 'Writing the answer…',
}

const CARD_UNAVAILABLE = 'The balance card could not be displayed.'

// Tools que el navegador ejecuta (apariencia) y las que solo dibuja (tarjetas)
const CLIENT_TOOLS = [...APPEARANCE_TOOLS, ...DISPLAY_TOOLS]

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

  // 1. Al abrir: trae el historial y se lo da al agente para que tenga el contexto.
  useEffect(() => {
    async function loadHistory() {
      try {
        const history = await getHistory(token, sessionId)
        const loaded: ChatMessage[] = history.map((m) => ({
          id: randomUUID(),
          role: m.role === 'human' ? 'user' : 'assistant',
          content: m.content,
          // Tarjeta guardada: se vuelve a dibujar con los mismos datos
          card: parseBalanceCard(m.card) ?? undefined,
        }))
        setMessages(loaded.map((m) => (m.card || m.content ? m : { ...m, content: CARD_UNAVAILABLE })))
        // Al agente solo le sirve el texto; las tarjetas ya están en el checkpoint del backend
        agent.setMessages(loaded.filter((m) => !m.card && m.content))
      } catch (err) {
        setError(toErrorMessage(err))
      } finally {
        setLoadingHistory(false)
      }
    }
    loadHistory()
  }, [agent, token, sessionId])

  async function handleSend(question: string) {
    // 2. Muestra la pregunta y se la entrega al agente.
    const userMessage: ChatMessage = { id: randomUUID(), role: 'user', content: question }
    setMessages((current) => [...current, userMessage])
    agent.addMessage(userMessage)
    setRunning(true)
    setError(null)

    // 3. Ejecuta el agente: cada evento AG-UI actualiza la pantalla apenas llega.
    //    Devuelve el resultado de cada tool del navegador que pidió el agente.
    async function runOnce(): Promise<ToolMessage[]> {
      const toolResults: ToolMessage[] = []
      await agent.runAgent(
        // El backend recibe qué tools tiene el navegador; si el agente pide una, llega como TOOL_CALL_*.
        { tools: CLIENT_TOOLS },
        {
          // El backend entra a un nodo del grafo: se muestra qué está haciendo.
          onStepStartedEvent: ({ event }) => {
            setStep(STEP_LABELS[event.stepName] ?? 'Working…')
          },
          // Empieza la respuesta: burbuja vacía y ya no hace falta el paso.
          onTextMessageStartEvent: ({ event }) => {
            setStep(null)
            setMessages((current) => [...current, { id: event.messageId, role: 'assistant', content: '' }])
          },
          // Llega un pedazo: textMessageBuffer es el texto ANTERIOR, por eso se le suma el delta.
          onTextMessageContentEvent: ({ event, textMessageBuffer }) => {
            const text = textMessageBuffer + event.delta
            setMessages((current) => current.map((m) => (m.id === event.messageId ? { ...m, content: text } : m)))
          },
          onToolCallEndEvent: ({ event, toolCallName, toolCallArgs }) => {
            // Tool de solo mostrar (tarjeta del saldo): se dibuja en el chat y no devuelve resultado
            if (isDisplayTool(toolCallName)) {
              const card = parseBalanceCard(toolCallArgs) ?? undefined
              // Datos rotos: se avisa en vez de dejar al usuario sin nada (el texto dice que hay una tarjeta)
              const content = card ? '' : CARD_UNAVAILABLE
              setMessages((current) => [...current, { id: event.toolCallId, role: 'assistant', content, card }])
              return
            }
            // El agente pidió una tool del navegador (tema, fondo, fuente): se aplica y se guarda su resultado.
            toolResults.push(runToolCall(event.toolCallId, toolCallName, toolCallArgs))
          },
          // El backend avisó un error dentro del stream.
          onRunErrorEvent: ({ event }) => {
            setError(event.message)
          },
        },
      )
      return toolResults
    }

    try {
      const toolResults = await runOnce()
      // 4. Avisa al padre para que refresque los títulos de la lista (aunque falle la confirmación).
      onRunFinished()
      // 5. Si se ejecutaron tools, se devuelven sus resultados en un run más y el agente confirma con texto.
      //    Ese run va directo a redactar (no pide tools), así que no hay un tercer run.
      if (toolResults.length > 0) {
        toolResults.forEach((result) => agent.addMessage(result))
        try {
          await runOnce()
          // La confirmación también consumió tokens: se refresca de nuevo
          onRunFinished()
        } catch (err) {
          // El estilo ya quedó aplicado: solo falló el mensaje de confirmación
          setError(`The change was applied, but the confirmation failed: ${toErrorMessage(err)}`)
        }
      }
    } catch (err) {
      // Fallas de red o HTTP (401, 404...) llegan acá.
      setError(toErrorMessage(err))
    } finally {
      setRunning(false)
      setStep(null)
    }
  }

  if (loadingHistory) {
    return (
      <div className="flex-grow-1 d-flex align-items-center justify-content-center">
        <span className="spinner-border text-primary" aria-label="Loading history" />
      </div>
    )
  }
  return <ChatPanel messages={messages} running={running} step={step} error={error} onSend={handleSend} />
}
