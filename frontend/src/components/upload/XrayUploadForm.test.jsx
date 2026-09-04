import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import XrayUploadForm from './XrayUploadForm'

const PATIENT_ID = 7
const PATIENT_NAME = 'Maria Santos'
const UPLOAD_URL = `/api/imaging/patients/${PATIENT_ID}/xray/upload/`
const TX_ID = '123e4567-e89b-12d3-a456-426614174000'
const ANALYSE_URL = `/api/imaging/xray/${TX_ID}/analyse/`
const CONFIRM_URL = `/api/imaging/patients/${PATIENT_ID}/xray/upload/confirm/${TX_ID}/`

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  })
}

function uploadFile(file = new File(['fake dicom bytes'], 'scan.dcm', { type: 'application/dicom' })) {
  const input = document.querySelector('input[type="file"]')
  fireEvent.change(input, { target: { files: [file] } })
  return file
}

describe('XrayUploadForm low-quality flow', () => {
  it('shows low-quality confirmation prompt when upload returns quality check response', async () => {
    const onSuccess = vi.fn()
    const fetchMock = vi.fn(() => jsonResponse({
      status: 'quality_check_failed',
      message: 'Uploaded image may be too low quality for reliable AI interpretation.',
      quality_score: 0.41,
      requires_confirmation: true,
      can_proceed: true,
      transaction_id: TX_ID,
    }))
    vi.stubGlobal('fetch', fetchMock)

    render(<XrayUploadForm patientId={PATIENT_ID} patientName={PATIENT_NAME} onSuccess={onSuccess} />)
    uploadFile()

    await userEvent.click(screen.getByRole('button', { name: /Upload X-ray/i }))

    expect(await screen.findByText('Low-quality image detected')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Proceed Anyway' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Re-upload' })).toBeInTheDocument()
    expect(onSuccess).not.toHaveBeenCalled()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe(UPLOAD_URL)
  })

  it('continues upload after Proceed Anyway using analyse(force_proceed) then upload-confirm', async () => {
    const onSuccess = vi.fn()
    const confirmedRecord = {
      transaction_id: TX_ID,
      status: 'AI_REVIEWED',
      upload_timestamp: '2026-09-04T08:00:00Z',
    }

    const fetchMock = vi.fn((url) => {
      if (url === UPLOAD_URL) {
        return jsonResponse({
          status: 'quality_check_failed',
          message: 'Uploaded image may be too low quality for reliable AI interpretation.',
          quality_score: 0.39,
          requires_confirmation: true,
          can_proceed: true,
          transaction_id: TX_ID,
        })
      }
      if (url === ANALYSE_URL) {
        return jsonResponse({ risk_label: 'LOW', risk_score: 0.23 }, 200)
      }
      if (url === CONFIRM_URL) {
        return jsonResponse(confirmedRecord, 200)
      }
      return jsonResponse({ detail: 'Unexpected URL' }, 500)
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<XrayUploadForm patientId={PATIENT_ID} patientName={PATIENT_NAME} onSuccess={onSuccess} />)
    uploadFile()

    await userEvent.click(screen.getByRole('button', { name: /Upload X-ray/i }))
    await userEvent.click(await screen.findByRole('button', { name: 'Proceed Anyway' }))

    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(confirmedRecord))

    const analyseCall = fetchMock.mock.calls.find(([url]) => url === ANALYSE_URL)
    expect(analyseCall).toBeDefined()
    expect(analyseCall[1].method).toBe('POST')
    expect(JSON.parse(analyseCall[1].body)).toEqual({ force_proceed: true })

    const confirmCall = fetchMock.mock.calls.find(([url]) => url === CONFIRM_URL)
    expect(confirmCall).toBeDefined()
    expect(confirmCall[1].method).toBe('GET')
  })

  it('resets upload state when Re-upload is chosen', async () => {
    const onSuccess = vi.fn()
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({
      status: 'quality_check_failed',
      message: 'Uploaded image may be too low quality for reliable AI interpretation.',
      quality_score: 0.41,
      requires_confirmation: true,
      can_proceed: true,
      transaction_id: TX_ID,
    })))

    render(<XrayUploadForm patientId={PATIENT_ID} patientName={PATIENT_NAME} onSuccess={onSuccess} />)
    uploadFile()
    expect(screen.getByText('scan.dcm')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Upload X-ray/i }))
    await userEvent.click(await screen.findByRole('button', { name: 'Re-upload' }))

    await waitFor(() => {
      expect(screen.queryByText('Low-quality image detected')).not.toBeInTheDocument()
    })
    expect(screen.queryByText('scan.dcm')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Upload X-ray/i })).toBeDisabled()
    expect(onSuccess).not.toHaveBeenCalled()
  })

  it('keeps normal upload path unchanged for non-low-quality responses', async () => {
    const onSuccess = vi.fn()
    const successPayload = {
      transaction_id: TX_ID,
      status: 'PENDING',
      upload_timestamp: '2026-09-04T08:00:00Z',
    }
    const fetchMock = vi.fn(() => jsonResponse(successPayload, 200))
    vi.stubGlobal('fetch', fetchMock)

    render(<XrayUploadForm patientId={PATIENT_ID} patientName={PATIENT_NAME} onSuccess={onSuccess} />)
    uploadFile()

    await userEvent.click(screen.getByRole('button', { name: /Upload X-ray/i }))

    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(successPayload))
    expect(screen.queryByText('Low-quality image detected')).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe(UPLOAD_URL)
  })

  it('does not dismiss the low-quality modal when backdrop is clicked', async () => {
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({
      status: 'quality_check_failed',
      message: 'Uploaded image may be too low quality for reliable AI interpretation.',
      quality_score: 0.41,
      requires_confirmation: true,
      can_proceed: true,
      transaction_id: TX_ID,
    })))

    render(<XrayUploadForm patientId={PATIENT_ID} patientName={PATIENT_NAME} onSuccess={vi.fn()} />)
    uploadFile()

    await userEvent.click(screen.getByRole('button', { name: /Upload X-ray/i }))
    expect(await screen.findByText('Low-quality image detected')).toBeInTheDocument()

    const backdrop = document.querySelector('div.fixed.inset-0.z-50')
    fireEvent.click(backdrop)

    expect(screen.getByText('Low-quality image detected')).toBeInTheDocument()
  })
})
