import type { UsageReport } from '../models/usage/usage-report.model'
import { formatDay, formatTokens, lastDays } from '../usage/usage-days'

interface UsageModalProps {
  report: UsageReport
  onClose: () => void
}

// Detalle del consumo de los últimos 7 días (los días sin consumo aparecen en cero).
export function UsageModal({ report, onClose }: UsageModalProps) {
  return (
    <>
      <div className="modal d-block" tabIndex={-1} role="dialog" aria-labelledby="usage-title" onClick={onClose}>
        <div className="modal-dialog modal-dialog-centered" onClick={(event) => event.stopPropagation()}>
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title" id="usage-title">
                Token usage
              </h5>
              <button type="button" className="btn-close" aria-label="Close" onClick={onClose} />
            </div>
            <div className="modal-body p-0">
              <table className="table table-sm mb-0 text-end">
                <thead>
                  <tr>
                    <th className="text-start ps-3">Day</th>
                    <th>Input</th>
                    <th>Output</th>
                    <th className="pe-3">Questions</th>
                  </tr>
                </thead>
                <tbody>
                  {lastDays(report, 7).map((usage) => (
                    <tr key={usage.day} className={usage.day === report.today ? 'fw-semibold' : undefined}>
                      <td className="text-start ps-3">{formatDay(usage.day)}</td>
                      <td>{formatTokens(usage.input_tokens)}</td>
                      <td>{formatTokens(usage.output_tokens)}</td>
                      <td className="pe-3">{usage.runs}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="modal-footer small text-body-secondary">Each day starts from zero at 00:00 (Bolivia time).</div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop show" />
    </>
  )
}
