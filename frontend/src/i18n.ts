import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  en: {
    translation: {
      appName: 'Unity',
      appTagline: 'People, care and community in one calm place.',
      auth: {
        churchId: 'Church ID',
        churchIdHint:
          'Only needed if your account belongs to multiple churches.',
        invalid: 'We could not sign you in. Check your details and try again.',
        password: 'Password',
        signIn: 'Sign in',
        signingIn: 'Signing in…',
        username: 'Username',
      },
      nav: {
        home: 'Home',
        people: 'People',
        events: 'Events',
        followUps: 'Follow-ups',
      },
      shell: {
        menu: 'Open navigation',
        roleAtChurch: '{{role}} at {{church}}',
        signOut: 'Sign out',
      },
      dashboard: {
        eyebrow: 'Today in your community',
        greeting: 'Welcome back, {{name}}',
        intro: 'Start with the people and actions that need your attention.',
        directoryTitle: 'People directory',
        directoryBody: 'Find people and keep contact details together.',
        eventsTitle: 'Upcoming events',
        eventsBody: 'Registration and check-in will appear here.',
        followUpsTitle: 'My follow-ups',
        followUpsBody: 'Assigned newcomer conversations will appear here.',
        comingSoon: 'Coming in the next milestone',
        openDirectory: 'Open directory',
      },
      directory: {
        allGroups: 'All groups',
        allStatuses: 'All statuses',
        allUniversities: 'All universities',
        call: 'Call',
        callPerson: 'Call {{name}}',
        clear: 'Clear filters',
        email: 'Email',
        emailPerson: 'Email {{name}}',
        emptyBody: 'People added to your church will appear here.',
        emptyTitle: 'Your directory is ready',
        errorBody: 'Check your connection and try loading the directory again.',
        errorTitle: 'We could not load people',
        eyebrow: 'People in your care',
        filters: 'Directory filters',
        group: 'Group',
        intro: 'Find someone quickly, then reach out in a tap.',
        loading: 'Loading people',
        noContext: 'Contact details available in their profile',
        noMatchesBody: 'Try a broader name or remove one of the filters.',
        noMatchesTitle: 'No people match these filters',
        peopleCount_one: ' person',
        peopleCount_other: ' people',
        results: 'People directory results',
        searchLabel: 'Search people by name',
        searchPlaceholder: 'Search by name…',
        status: 'Status',
        statuses: {
          inactive: 'Inactive',
          member: 'Member',
          newcomer: 'Newcomer',
          regular: 'Regular',
          visitor: 'Visitor',
        },
        title: 'People directory',
        tryAgain: 'Try again',
        university: 'University',
      },
      loading: 'Preparing Unity…',
      notFound: {
        title: 'Page not found',
        body: 'This page is not part of Unity yet.',
        action: 'Return home',
      },
    },
  },
} as const

void i18n.use(initReactI18next).init({
  resources,
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export default i18n
