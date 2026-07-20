import { describe, expect, it } from 'vitest'

import {
  validateEventForm,
  type EventFormValidationInput,
} from './eventFormValidation'

const validForm: EventFormValidationInput = {
  id: null,
  title: 'Welcome lunch',
  starts_at: '2026-07-25T12:00',
  ends_at: '2026-07-25T14:00',
  signup_closes_at: '2026-07-25T10:00',
}

const now = new Date('2026-07-20T12:00').getTime()

describe('validateEventForm', () => {
  it('requires a title, start time, and end time', () => {
    expect(
      validateEventForm(
        {
          ...validForm,
          title: ' ',
          starts_at: '',
          ends_at: '',
        },
        now,
      ),
    ).toEqual({
      title: 'titleRequired',
      starts_at: 'startRequired',
      ends_at: 'endRequired',
    })
  })

  it('rejects a past start time for a new event', () => {
    expect(
      validateEventForm(
        {
          ...validForm,
          starts_at: '2026-07-19T12:00',
          ends_at: '2026-07-19T14:00',
          signup_closes_at: '2026-07-19T10:00',
        },
        now,
      ),
    ).toEqual({ starts_at: 'startInPast' })
  })

  it('allows a past start time when editing an existing event', () => {
    expect(
      validateEventForm(
        {
          ...validForm,
          id: 42,
          starts_at: '2026-07-19T12:00',
          ends_at: '2026-07-19T14:00',
          signup_closes_at: '2026-07-19T10:00',
        },
        now,
      ),
    ).toEqual({})
  })

  it('requires the end time to be later than the start time', () => {
    expect(
      validateEventForm(
        {
          ...validForm,
          ends_at: validForm.starts_at,
        },
        now,
      ),
    ).toEqual({ ends_at: 'endBeforeStart' })
  })

  it('rejects a signup close time later than the start time', () => {
    expect(
      validateEventForm(
        {
          ...validForm,
          signup_closes_at: '2026-07-25T12:01',
        },
        now,
      ),
    ).toEqual({ signup_closes_at: 'signupAfterStart' })
  })

  it('accepts valid event dates and fields', () => {
    expect(validateEventForm(validForm, now)).toEqual({})
  })
})
