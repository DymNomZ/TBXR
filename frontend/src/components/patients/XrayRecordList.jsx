import { Clock, FileDown } from 'lucide-react';
import { useState, useEffect } from 'react'
import { useAuth } from '../../context/AuthContext'
import StatusBadge from '../ui/StatusBadge'
import Modal from '../ui/Modal'
import HeatmapViewer from '../imaging/HeatmapViewer'
import StaticAnnotationOverlay from '../imaging/StaticAnnotationOverlay'
import AIRiskBadge from '../ui/AIRiskBadge'
import Button from '../ui/Button'

function XrayRecordItem({ record, onClick }) {

  return (
    <div 
    onClick={onClick}
    className="flex flex-col gap-1.5 p-4 rounded-xl border border-[var(--border)] hover:bg-[var(--surface-soft)] hover:border-[var(--accent)] transition-colors cursor-pointer"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-[var(--deep-navy)] font-mono">
          {record.transaction_id}
        </span>
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={record.status} />
          {record.ai_result && (
            <AIRiskBadge
              label={record.ai_result.risk_label}
              score={record.ai_result.risk_score}
            />
          )}
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
        <span>{new Date(record.upload_timestamp).toLocaleString('en-PH')}</span>
        {/* <span>{record.view_type}</span> */}
      </div>

      {record.reviewing_doctor && (
        <div className="text-xs text-[var(--text-muted)] text-right">
          {/* {record.reviewing_doctor} */}
        </div>
      )}
    </div>
  );
}

export default function XrayRecordList({ patientId, refreshKey = 0, autoOpenTransactionId = null }) {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedRecord, setSelected] = useState(null)  // ← tracks clicked record
  const [transform, setTransform] = useState({ scale: 1, translate: { x: 0, y: 0 } })
  const [xrayData,  setXrayData]  = useState(null)
  const { user } = useAuth()

  // Reset when modal closes — update your setSelected(null) calls:
  const handleClose = () => {
    setSelected(null)
    setXrayData(null)
  }

  useEffect(() => {
    if (!selectedRecord) return
    const controller = new AbortController()
    setXrayData(null)
    fetch(`/api/imaging/xray/${selectedRecord.transaction_id}/`, {
      credentials: 'include',
      signal: controller.signal,
    })
      .then((r) => r.json())
      .then(setXrayData)
      .catch((err) => {
        if (err.name !== 'AbortError') console.error(err)
      })
    return () => controller.abort()
  }, [selectedRecord?.transaction_id])

  useEffect(() => {
    if (!patientId) return
    setLoading(true)
    fetch(`/api/imaging/patients/${patientId}/xray/`, {
      credentials: 'include',
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => { setRecords(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [patientId, refreshKey])

   useEffect(() => {
    if (!autoOpenTransactionId || records.length === 0) return
    const match = records.find(r => r.transaction_id === autoOpenTransactionId)
    if (match) setSelected(match)
  }, [autoOpenTransactionId, records])  // runs when records finish loading

  if (loading) return (
    <div className="bg-white rounded-2xl border border-[var(--border)] shadow-sm p-6">
      <p className="text-sm text-[var(--text-muted)] text-center py-8">
        Loading records...
      </p>
    </div>
  )

  return (
    <>
      <div className="bg-white rounded-2xl border border-[var(--border)] shadow-sm p-6 flex flex-col gap-4">
        {/* Card header */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-[var(--accent-soft)] flex items-center justify-center">
            <Clock size={16} className="text-[var(--accent)]" />
          </div>
          <h2 className="text-base font-bold text-[var(--deep-navy)]">X-Ray Record History</h2>
          {records.length > 0 && (
            <span className="ml-auto text-xs font-semibold bg-[var(--accent-soft)] text-[var(--accent)] px-2.5 py-1 rounded-full">
              {records.length} record{records.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        {/* Records */}
        {records.length > 0 ? (
          <div className="flex flex-col gap-2">
            {records.map((record) => (
              <XrayRecordItem
                key={record.transaction_id}
                record={record}
                onClick={() => setSelected(record)}
              />
            ))}
          </div>
        ) : (
          // Empty state — expected initially per the task
          <div className="flex flex-col items-center justify-center py-12 text-center gap-2">
            <div className="w-12 h-12 rounded-full bg-[var(--surface-soft)] flex items-center justify-center mb-1">
              <Clock size={22} className="text-[var(--text-muted)]" />
            </div>
            <p className="text-sm font-medium text-[var(--text)]">No records yet</p>
            <p className="text-xs text-[var(--text-muted)]">
              X-ray records will appear here once uploads come in.
            </p>
          </div>
        )}
      </div>

      {/* Viewer modal */}
      <Modal
        isOpen={!!selectedRecord}
        onClose={handleClose}
        title={selectedRecord?.transaction_id ?? ''}
        size="lg"
      >
        {selectedRecord && (
          <div className="flex flex-col gap-5">

            {/* Viewer with static overlay */}
            <HeatmapViewer
              rawImageUrl={xrayData?.display_image ?? null}
              heatmapUrl={xrayData?.ai_result?.heatmap_url ?? null}
              onTransformChange={setTransform}
              overlay={
                <StaticAnnotationOverlay
                  annotations={xrayData?.annotations ?? []}
                  scale={transform.scale}
                  translate={transform.translate}
                />
              }
            />

            {/* Radiologist notes — one card per annotation */}
            {xrayData?.annotations?.length > 0 && (
              <div className="flex flex-col gap-3">
                <h3 className="text-sm font-bold text-[var(--deep-navy)]">Radiologist Notes</h3>
                {xrayData.annotations.map((ann, i) => (
                  <div
                    key={i}
                    className="flex flex-col gap-1.5 p-4 rounded-xl bg-[var(--surface-soft)] border border-[var(--border)]"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-[var(--accent)]">
                        {ann.radiologist
                          ? `${ann.radiologist.first_name} ${ann.radiologist.last_name}`
                          : 'Unknown'}
                      </span>
                      <span className="text-xs text-[var(--text-muted)]">
                        {new Date(ann.submitted_at).toLocaleString('en-PH')}
                      </span>
                    </div>
                    {ann.notes ? (
                      <p className="text-sm text-[var(--text)] leading-relaxed">{ann.notes}</p>
                    ) : (
                      <p className="text-sm text-[var(--text-muted)] italic">No notes provided.</p>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Generate Report */}
            {selectedRecord?.status === 'COMPLETED' && user?.role === 'RADIOLOGIST' && (
            <Button
              variant="secondary"
              fullWidth
              onClick={() => window.open(`/api/imaging/xray/${selectedRecord.transaction_id}/report/`, '_blank')}
            >
              <FileDown size={15} />
              Generate Report
            </Button>
          )}

          </div>
        )}
      </Modal>
    </>
  );
}