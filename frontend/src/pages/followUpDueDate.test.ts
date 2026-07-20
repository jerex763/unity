import { describe, expect, it } from 'vitest'

import { classifyFollowUpDueDate } from './followUpDueDate'

describe('classifyFollowUpDueDate', () => {
  const today = '2026-07-20'

  it('classifies a missing due date', () => {
    expect(classifyFollowUpDueDate(null, today)).toBe('none')
  })

  it('classifies an overdue date', () => {
    expect(classifyFollowUpDueDate('2026-07-19', today)).toBe('overdue')
  })

  it('classifies a date due today', () => {
    expect(classifyFollowUpDueDate(today, today)).toBe('today')
  })

  it('classifies a future due date', () => {
    expect(classifyFollowUpDueDate('2026-07-21', today)).toBe('future')
  })
})
