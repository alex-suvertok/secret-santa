"""Secret Santa assignment algorithm.

Given every member's eligible recipients ("colleagues"), find a valid exchange
where every member gives exactly once and receives exactly once:

* self-gifts are forbidden;
* the best outcome is a single connected cycle (everyone is linked in one row),
  so 1:1 mutual gifts and closed mini-circles are avoided whenever possible;
* a 1:1 mutual exchange is used only as a last resort;
* if no valid assignment exists, a user-friendly AssignmentError is raised.
"""

import random


class AssignmentError(Exception):
    """Raised when no valid Secret Santa assignment can be built."""


# Sanity cap: with realistic team sizes a valid assignment is found almost
# immediately; these bounds guard against pathological (but feasible) graphs.
HAMILTONIAN_ATTEMPTS = 200
HAMILTONIAN_STEP_BUDGET = 4000
GREEDY_ATTEMPTS = 2000


def build_member_to_candidates(members):
    """Return {member: [eligible recipients]} excluding the member itself.

    Raises AssignmentError when a member has no one to give a gift to.
    """
    result = {}
    for member in members:
        candidates = [c for c in member.colleagues.all() if c.pk != member.pk]
        if not candidates:
            raise AssignmentError(
                f'Учасник "{member}" не має жодного колеги, якому можна дарувати подарунок. '
                'Налаштуйте поле "colleagues".'
            )
        result[member] = candidates
    return result


def _is_assignment_possible(members, member_to_candidates):
    """Kuhn's maximum bipartite matching (givers -> recipients).

    Returns True iff every member can give to a unique recipient.
    """
    members_by_pk = {member.pk: member for member in members}
    recipient_to_giver = {}  # recipient.pk -> giver.pk

    def try_augment(giver, visited):
        for recipient in member_to_candidates[giver]:
            recipient_pk = recipient.pk
            if recipient_pk in visited:
                continue
            visited.add(recipient_pk)
            if (
                recipient_pk not in recipient_to_giver
                or try_augment(members_by_pk[recipient_to_giver[recipient_pk]], visited)
            ):
                recipient_to_giver[recipient_pk] = giver.pk
                return True
        return False

    for giver in members:
        try_augment(giver, set())

    return len(recipient_to_giver) == len(members)


def _decompose_into_cycles(assignment, members):
    """Split the assignment into cycles, return the list of their lengths."""
    visited = set()
    cycles = []
    for member in members:
        if member.pk in visited:
            continue
        current = member
        length = 0
        while current.pk not in visited:
            visited.add(current.pk)
            current = assignment[current]
            length += 1
        cycles.append(length)
    return cycles


def _assignment_quality(assignment, members):
    """Lower is better: fewer mutual(2-)cycles, longer shortest cycle, fewer cycles."""
    cycles = _decompose_into_cycles(assignment, members)
    mutual_exchanges = sum(1 for length in cycles if length == 2)
    return (mutual_exchanges, -min(cycles), len(cycles))


def _find_hamiltonian_cycle(members, member_to_candidates):
    """Try to build one single cycle covering every member (MRV backtracking)."""
    if len(members) < 2:
        return None

    for _ in range(HAMILTONIAN_ATTEMPTS):
        path = [random.choice(members)]
        visited = {path[0].pk}
        steps = 0

        def extend_tail():
            nonlocal steps
            steps += 1
            if steps > HAMILTONIAN_STEP_BUDGET:
                return None
            if len(path) == len(members):
                if path[0].pk in {c.pk for c in member_to_candidates[path[-1]]}:
                    return list(path)
                return None
            candidates = [
                c for c in member_to_candidates[path[-1]] if c.pk not in visited
            ]
            if not candidates:
                return None
            # MRV: prefer extending towards members with the fewest free options,
            # tie-broken randomly.
            random.shuffle(candidates)
            candidates.sort(key=lambda c: sum(1 for nxt in member_to_candidates[c] if nxt.pk not in visited))
            for candidate in candidates:
                path.append(candidate)
                visited.add(candidate.pk)
                cycle = extend_tail()
                if cycle is not None:
                    return cycle
                visited.discard(candidate.pk)
                path.pop()
            return None

        cycle = extend_tail()
        if cycle is not None:
            return cycle
    return None


def _greedy_assignment(members, member_to_candidates):
    """One randomized MRV construction. Returns {giver: recipient} or None."""
    unassigned_givers = list(members)
    available_recipients = {m.pk: m for m in members}
    assignment = {}

    while unassigned_givers:
        def available_options(giver):
            return [c for c in member_to_candidates[giver] if c.pk in available_recipients]

        # MRV: the giver with the fewest remaining options goes first; ties random.
        random.shuffle(unassigned_givers)
        unassigned_givers.sort(key=lambda g: len(available_options(g)))
        giver = unassigned_givers[0]
        options = available_options(giver)
        if not options:
            return None
        recipient = random.choice(options)
        assignment[giver] = recipient
        unassigned_givers.remove(giver)
        del available_recipients[recipient.pk]

    return assignment


def build_assignment(members):
    """Return {giver: recipient} for a valid exchange.

    Prefers a single connected cycle, then the quality of the fallback keeps
    mutual gifts and closed mini-circles as rare as possible.
    """
    member_to_candidates = build_member_to_candidates(members)

    if not _is_assignment_possible(members, member_to_candidates):
        raise AssignmentError(
            f'Неможливо побудувати обмін подарунками для {len(members)} учасників '
            'за поточних обмежень "colleagues". Змініть поля "colleagues" та спробуйте ще раз.'
        )

    # Best possible outcome: one connected row (single cycle).
    cycle_members = _find_hamiltonian_cycle(members, member_to_candidates)
    if cycle_members is not None:
        size = len(cycle_members)
        return {giver: cycle_members[(i + 1) % size] for i, giver in enumerate(cycle_members)}

    # Fallback: randomized constructions, keep the best cycle structure.
    best_assignment = None
    best_quality = None

    for _ in range(GREEDY_ATTEMPTS):
        assignment = _greedy_assignment(members, member_to_candidates)
        if assignment is None:
            continue
        quality = _assignment_quality(assignment, members)
        if best_quality is None or quality < best_quality:
            best_assignment = assignment
            best_quality = quality
        if best_quality == (0, -len(members), 1):
            break

    if best_assignment is None:
        raise AssignmentError(
            'Не вдалося побудувати обмін подарунками, хоча він існує. '
            'Спробуйте ще раз або змініть поля "colleagues".'
        )
    return best_assignment