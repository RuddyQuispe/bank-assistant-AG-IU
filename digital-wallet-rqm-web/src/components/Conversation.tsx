import { useEffect, useState } from 'react'
import { randomUUID } from '@ag-ui/client'
import { createWalletAgent } from '../api/agent'
import { toErrorMessage } from '../api/config'
import { getHistory } from '../api/sessions'
import { APPEARANCE_TOOLS, runAppearanceTool } from '../tools/appearance-tools'
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
        }))
        setMessages(loaded)
        agent.setMessages(loaded)
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
    try {
      await agent.runAgent(
        // El backend recibe qué tools tiene el navegador; si el agente pide una, llega como TOOL_CALL_*.
        { tools: APPEARANCE_TOOLS },
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
          // El agente pidió una tool del navegador (tema, fondo, fuente): toolCallArgs ya viene parseado.
          onToolCallEndEvent: ({ toolCallName, toolCallArgs }) => {
            // Un fallo al aplicar el estilo no debe cortar el stream de la respuesta
            try {
              runAppearanceTool(toolCallName, toolCallArgs)
            } catch (err) {
              console.error('Appearance tool failed', toolCallName, err)
            }
          },
          // El backend avisó un error dentro del stream.
          onRunErrorEvent: ({ event }) => {
            setError(event.message)
          },
        },
      )
      // 4. Avisa al padre para que refresque los títulos de la lista.
      onRunFinished()
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
