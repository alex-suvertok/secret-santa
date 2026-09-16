from django.test import TestCase

from .assignment import (
    AssignmentError,
    _assignment_quality,
    build_assignment,
)
from .models import Celebration, Member, SecretSanta, Team


class FakeColleagues:
    def __init__(self, members):
        self._members = members

    def all(self):
        return self._members


class FakeMember:
    def __init__(self, pk, name, colleagues=()):
        self.pk = pk
        self.name = name
        self.colleagues = FakeColleagues(list(colleagues))

    def __str__(self):
        return self.name


def fully_connected(pks):
    members = [FakeMember(pk, chr(ord('A') + pk)) for pk in pks]
    for member in members:
        member.colleagues = FakeColleagues([other for other in members if other.pk != member.pk])
    return members


class BuildAssignmentTests(TestCase):
    def test_single_cycle_preferred(self):
        members = fully_connected(range(6))
        assignment = build_assignment(members)
        self.assertEqual(len(assignment), 6)
        self.assertEqual(set(assignment.values()), set(members))
        for giver, recipient in assignment.items():
            self.assertNotEqual(giver, recipient)
            self.assertIn(recipient, giver.colleagues.all())
        quality = _assignment_quality(assignment, members)
        self.assertEqual(quality, (0, -6, 1))

    def test_no_self_and_valid_bijection(self):
        members = fully_connected(range(5))
        for _ in range(10):
            assignment = build_assignment(members)
            self.assertEqual(set(assignment), set(members))
            self.assertEqual(set(assignment.values()), set(members))
            self.assertTrue(all(g != r for g, r in assignment.items()))

    def test_disconnected_groups_still_valid(self):
        group_a = fully_connected(range(3))
        group_b = fully_connected(range(3, 6))
        for other in group_b:
            group_a[0].colleagues = FakeColleagues(group_a[0].colleagues.all() + [other])
        members = group_a + group_b
        assignment = build_assignment(members)
        self.assertEqual(set(assignment), set(members))
        self.assertEqual(len(set(assignment.values())), 6)
        self.assertTrue(all(g != r for g, r in assignment.items()))

    def test_member_without_colleagues_raises(self):
        a = FakeMember(0, 'A')
        b = FakeMember(1, 'B', [a])
        a.colleagues = FakeColleagues([])
        with self.assertRaisesMessage(AssignmentError, 'жодного колеги'):
            build_assignment([a, b])

    def test_impossible_layout_raises(self):
        a = FakeMember(0, 'A', [])
        b = FakeMember(1, 'B', [])
        c = FakeMember(2, 'C', [])
        a.colleagues = FakeColleagues([b])
        b.colleagues = FakeColleagues([a])
        c.colleagues = FakeColleagues([a])
        with self.assertRaises(AssignmentError):
            build_assignment([a, b, c])

    def test_two_members_allow_mutual_gift(self):
        a = FakeMember(0, 'A')
        b = FakeMember(1, 'B')
        a.colleagues = FakeColleagues([b])
        b.colleagues = FakeColleagues([a])
        assignment = build_assignment([a, b])
        self.assertEqual(assignment[a], b)
        self.assertEqual(assignment[b], a)


class CelebrationRunTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name='Test Team')
        users = []
        members = []
        for pk in range(6):
            member = Member.objects.create(
                team=self.team, name=f'Member {pk}', email_address=f'm{pk}@example.com'
            )
            members.append(member)
        for member in members:
            member.colleagues.set([other for other in members if other != member])
        self.members = members
        self.celebration = Celebration.objects.create(team=self.team, year=2030)

    def test_run_creates_valid_exchange(self):
        self.celebration.run()
        rows = SecretSanta.objects.filter(celebration=self.celebration)
        self.assertEqual(rows.count(), 6)
        self.assertEqual(set(rows.values_list('santa_id', flat=True)), set(self.celebration.team.members.values_list('id', flat=True)))
        self.assertEqual(set(rows.values_list('recipient_id', flat=True)), set(self.celebration.team.members.values_list('id', flat=True)))
        for row in rows:
            self.assertNotEqual(row.santa_id, row.recipient_id)

    def test_run_is_rerunnable(self):
        self.celebration.run()
        first = {r.recipient_id for r in SecretSanta.objects.filter(celebration=self.celebration)}
        self.celebration.run()
        self.assertEqual(
            SecretSanta.objects.filter(celebration=self.celebration).count(), 6
        )

    def test_members_can_participate_in_other_celebrations(self):
        other_team = Team.objects.create(name='Other Team')
        other_members = [
            Member.objects.create(team=other_team, name=f'X {pk}', email_address=f'x{pk}@example.com')
            for pk in range(4)
        ]
        for member in other_members:
            member.colleagues.set([o for o in other_members if o != member])
        Celebration.objects.create(team=other_team, year=2030).run()
        self.celebration.run()
        self.assertTrue(SecretSanta.objects.filter(celebration=self.celebration).exists())
        self.assertTrue(SecretSanta.objects.filter(celebration__team=other_team).exists())

    def test_failed_run_keeps_existing_rows(self):
        self.celebration.run()
        self.members[0].colleagues.clear()
        with self.assertRaises(AssignmentError):
            self.celebration.run()
        self.assertEqual(
            SecretSanta.objects.filter(celebration=self.celebration).count(), 6
        )