from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import ChurchMembership, User
from care.models import CareCase, FollowUp, Interaction
from events.models import Event, EventRegistration
from groups.models import Group, GroupMembership
from people.models import Household, Person, Relationship
from tenancy.models import Church

pytestmark = pytest.mark.django_db


@pytest.fixture
def church() -> Church:
    return Church.objects.create(name="Harbour Community Church")


@pytest.fixture
def other_church() -> Church:
    return Church.objects.create(name="Hills Community Church")


@pytest.fixture
def user() -> User:
    return User.objects.create_user(username="fictional.worker")


@pytest.fixture
def person(church: Church) -> Person:
    return Person.objects.create(church=church, full_name="Jordan Example")


def test_optional_email_is_unique_within_a_church(
    church: Church,
    other_church: Church,
) -> None:
    Person.objects.create(
        church=church,
        full_name="Alex Example",
        email="fictional@example.test",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Person.objects.create(
            church=church,
            full_name="Casey Example",
            email="fictional@example.test",
        )

    Person.objects.create(
        church=other_church,
        full_name="Morgan Example",
        email="fictional@example.test",
    )
    Person.objects.create(church=church, full_name="No Email One")
    Person.objects.create(church=church, full_name="No Email Two")


def test_person_rejects_household_from_another_church(
    church: Church,
    other_church: Church,
) -> None:
    household = Household.objects.create(
        church=other_church,
        name="Example Household",
    )
    person = Person(
        church=church,
        full_name="Taylor Example",
        household=household,
    )

    with pytest.raises(ValidationError, match="same church"):
        person.full_clean()


def test_relationship_is_canonical_and_unique(church: Church) -> None:
    first = Person.objects.create(church=church, full_name="First Example")
    second = Person.objects.create(church=church, full_name="Second Example")

    relationship = Relationship.objects.create(
        church=church,
        from_person=second,
        to_person=first,
        kind=Relationship.Kind.FRIEND,
    )
    relationship.refresh_from_db()

    assert relationship.from_person_id == min(first.id, second.id)
    assert relationship.to_person_id == max(first.id, second.id)

    with pytest.raises(IntegrityError), transaction.atomic():
        Relationship.objects.create(
            church=church,
            from_person=first,
            to_person=second,
            kind=Relationship.Kind.FRIEND,
        )

    with pytest.raises(IntegrityError), transaction.atomic():
        Relationship.objects.create(
            church=church,
            from_person=first,
            to_person=first,
            kind=Relationship.Kind.FAMILY,
        )


def test_church_membership_person_must_share_its_church(
    church: Church,
    other_church: Church,
    user: User,
) -> None:
    person = Person.objects.create(
        church=other_church,
        full_name="Cross Church Example",
    )
    membership = ChurchMembership(
        user=user,
        church=church,
        person=person,
        role=ChurchMembership.Role.LEADER,
    )

    with pytest.raises(ValidationError, match="same church"):
        membership.full_clean()


def test_only_one_active_group_membership_is_allowed(
    church: Church,
    person: Person,
) -> None:
    group = Group.objects.create(
        church=church,
        name="Example Group",
        kind=Group.Kind.SMALL_GROUP,
    )
    GroupMembership.objects.create(
        church=church,
        group=group,
        person=person,
        role=GroupMembership.Role.MEMBER,
        joined_at=date(2026, 1, 1),
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        GroupMembership.objects.create(
            church=church,
            group=group,
            person=person,
            role=GroupMembership.Role.LEADER,
            joined_at=date(2026, 2, 1),
        )

    GroupMembership.objects.filter(group=group, person=person).update(
        left_at=date(2026, 2, 28)
    )
    GroupMembership.objects.create(
        church=church,
        group=group,
        person=person,
        role=GroupMembership.Role.LEADER,
        joined_at=date(2026, 3, 1),
    )


def test_event_time_and_capacity_constraints(church: Church, user: User) -> None:
    starts_at = timezone.now()

    with pytest.raises(IntegrityError), transaction.atomic():
        Event.objects.create(
            church=church,
            title="Invalid Time Event",
            starts_at=starts_at,
            ends_at=starts_at,
            created_by=user,
        )

    with pytest.raises(IntegrityError), transaction.atomic():
        Event.objects.create(
            church=church,
            title="Invalid Capacity Event",
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            capacity=0,
            created_by=user,
        )


def test_event_registration_is_unique_and_church_scoped(
    church: Church,
    other_church: Church,
    person: Person,
    user: User,
) -> None:
    event = Event.objects.create(
        church=church,
        title="Example Event",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timedelta(hours=1),
        created_by=user,
    )
    EventRegistration.objects.create(
        church=church,
        event=event,
        person=person,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        EventRegistration.objects.create(
            church=church,
            event=event,
            person=person,
        )

    other_person = Person.objects.create(
        church=other_church,
        full_name="Other Church Example",
    )
    invalid_registration = EventRegistration(
        church=church,
        event=event,
        person=other_person,
    )
    with pytest.raises(ValidationError, match="share a church"):
        invalid_registration.full_clean()


def test_person_has_only_one_open_follow_up(
    church: Church,
    person: Person,
) -> None:
    FollowUp.objects.create(
        church=church,
        person=person,
        source=FollowUp.Source.EVENT_VISIT,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        FollowUp.objects.create(
            church=church,
            person=person,
            source=FollowUp.Source.FRIEND_INVITE,
        )

    FollowUp.objects.filter(person=person).update(status=FollowUp.Status.CLOSED)
    FollowUp.objects.create(
        church=church,
        person=person,
        source=FollowUp.Source.FRIEND_INVITE,
    )


def test_interaction_has_at_most_one_context(
    church: Church,
    person: Person,
    user: User,
) -> None:
    follow_up = FollowUp.objects.create(
        church=church,
        person=person,
        source=FollowUp.Source.WALK_IN,
    )
    care_case = CareCase.objects.create(
        church=church,
        person=person,
        kind=CareCase.Kind.PRACTICAL,
        title="Fictional support request",
        details="Fictional test details only.",
        created_by=user,
    )

    Interaction.objects.create(
        church=church,
        person=person,
        author=user,
        kind=Interaction.Kind.MESSAGE,
        summary="Fictional general interaction.",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Interaction.objects.create(
            church=church,
            person=person,
            author=user,
            kind=Interaction.Kind.MEETING,
            summary="Invalid dual-context interaction.",
            follow_up=follow_up,
            care_case=care_case,
        )
