# Audit log retention

Unity retains security audit events for 24 months by default. This covers routine
incident review and access investigations while avoiding indefinite storage of
activity history.

Audit entries contain identifiers and deliberately small, allow-listed metadata;
they never contain passwords, authentication tokens, contact details, care notes,
person notes, or before/after copies of changed fields.

Normal application and Django Admin code cannot edit or delete an audit event.
Any retention purge must be an explicit, separately reviewed operational process
run by an authorized administrator. Suspend deletion when an incident, complaint,
legal hold, or active investigation requires preservation. Review the 24-month
period before production use and whenever regulatory or church governance
requirements change.
