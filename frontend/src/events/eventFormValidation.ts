export type EventFormValidationInput = {
  id: number | null
  title: string
  starts_at: string
  ends_at: string
  signup_closes_at: string
}

export type EventFormValidationField =
  'title' | 'starts_at' | 'ends_at' | 'signup_closes_at'

export type EventFormValidationError =
  | 'titleRequired'
  | 'startRequired'
  | 'startInPast'
  | 'endRequired'
  | 'endBeforeStart'
  | 'signupAfterStart'

export function validateEventForm(
  form: EventFormValidationInput,
  now = Date.now(),
): Partial<Record<EventFormValidationField, EventFormValidationError>> {
  const errors: Partial<
    Record<EventFormValidationField, EventFormValidationError>
  > = {}
  const startsAt = new Date(form.starts_at)
  const endsAt = new Date(form.ends_at)
  const signupClosesAt = new Date(form.signup_closes_at)
  const hasValidStart =
    form.starts_at !== '' && !Number.isNaN(startsAt.getTime())

  if (!form.title.trim()) errors.title = 'titleRequired'

  if (!hasValidStart) {
    errors.starts_at = 'startRequired'
  } else if (!form.id && startsAt.getTime() < now) {
    errors.starts_at = 'startInPast'
  }

  if (!form.ends_at || Number.isNaN(endsAt.getTime())) {
    errors.ends_at = 'endRequired'
  } else if (hasValidStart && endsAt.getTime() <= startsAt.getTime()) {
    errors.ends_at = 'endBeforeStart'
  }

  if (
    form.signup_closes_at &&
    !Number.isNaN(signupClosesAt.getTime()) &&
    hasValidStart &&
    signupClosesAt.getTime() > startsAt.getTime()
  ) {
    errors.signup_closes_at = 'signupAfterStart'
  }

  return errors
}
