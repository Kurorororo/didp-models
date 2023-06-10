import copy
from collections import deque


def read_wt(filename):
    processing_times = []
    due_dates = []
    weights = []

    with open(filename) as f:
        n = int(f.readline().strip())

        for _ in range(n):
            row = f.readline().split()
            processing_times.append(int(row[0]))
            due_dates.append(int(row[1]))
            weights.append(int(row[2]))

    return processing_times, due_dates, weights


def read_wet(filename):
    processing_times = []
    due_dates = []
    earliness_weights = []
    tardiness_weights = []

    with open(filename) as f:
        n = int(f.readline().strip())

        for _ in range(n):
            row = f.readline().split()
            processing_times.append(int(row[0]))
            due_dates.append(int(row[1]))
            earliness_weights.append(int(row[2]))
            tardiness_weights.append(int(row[3]))

    return processing_times, due_dates, earliness_weights, tardiness_weights


def read_wt_prec(filename):
    processing_times = []
    due_dates = []
    weights = []
    before = []
    after = []

    with open(filename) as f:
        n = int(f.readline().strip())

        for _ in range(n):
            row = f.readline().split()
            processing_times.append(int(row[0]))
            due_dates.append(int(row[1]))
            weights.append(int(row[2]))
            before.append(set())
            after.append(set())

        while f.readline():
            row = f.readline().split()
            i = int(row[0])
            j = int(row[1])
            before[j].add(i)
            after[i].add(j)

    return processing_times, due_dates, weights, before, after


def compute_completion_times(solution, processing_times, before=None):
    if len(solution) != len(processing_times):
        print(
            "The length of the solution {} mismatches the actual length {}".format(
                len(solution), len(processing_times)
            )
        )

    completion_times = [0 for _ in solution]
    scheduled = set()
    t = 0

    for j in solution:
        if j < 0 or j >= len(processing_times):
            print("No such job {}".format(j))
            return None

        if j in scheduled:
            print("Job {} is already scheduled".format(j))
            return None

        if before is not None and len(before[j] - scheduled) > 0:
            print(
                "Predecessors {} for job {} are not scheduled".format(
                    before[j] - scheduled, j
                )
            )
            return None

        t += processing_times[j]
        completion_times[j] = t
        scheduled.add(j)

    return completion_times


def verify_wt(solution, processing_times, due_dates, weights, before=None, cost=None):
    completion_times = compute_completion_times(
        solution, processing_times, before=before
    )

    if completion_times is None:
        return False, None

    actual_cost = sum(
        weights[i] * max(0, completion_times[i] - due_dates[i])
        for i in range(len(solution))
    )

    if cost is not None:
        if actual_cost != cost:
            print(
                "The cost of the solution {} mismatches the actual cost {}".format(
                    cost, actual_cost
                )
            )
            return False, None

    return True, actual_cost


def verify_max_wt(
    solution, processing_times, due_dates, weights, before=None, cost=None
):
    completion_times = compute_completion_times(
        solution, processing_times, before=before
    )

    if completion_times is None:
        return False, None

    actual_cost = max(
        weights[i] * max(0, completion_times[i] - due_dates[i])
        for i in range(len(solution))
    )

    if cost is not None:
        if actual_cost != cost:
            print(
                "The cost of the solution {} mismatches the actual cost {}".format(
                    cost, actual_cost
                )
            )
            return False, None

    return True, actual_cost


def verify_wet(
    solution,
    cost,
    processing_times,
    due_dates,
    earliness_weights,
    tardiness_weights,
    before=None,
):
    completion_times = compute_completion_times(
        solution, processing_times, before=before
    )

    if completion_times is None:
        return False

    actual_cost = sum(
        earliness_weights[i] * max(0, due_dates[i] - completion_times[i])
        + tardiness_weights[i] * max(0, completion_times[i] - due_dates[i])
        for i in range(len(solution))
    )

    if actual_cost != cost:
        print(
            "The cost of the solution {} mismatches the actual cost {}".format(
                cost, actual_cost
            )
        )
        return False

    return True


def extract_precedence_for_wt(processing_times, due_dates, weights):
    jobs = list(range(len(processing_times)))
    before = [set() for _ in jobs]
    after = [set() for _ in jobs]
    change = True

    while change:
        change = False
        for i in jobs:
            for j in jobs:
                if (
                    i != j
                    and i not in before[j]
                    and not has_path(j, i, after)
                    and check_kanet_conditions(
                        i, j, processing_times, due_dates, weights, before, after
                    )
                ):
                    before[j].add(i)
                    after[i].add(j)
                    change = True

    return before, after


def extract_precedence_for_wt_prec(processing_times, due_dates, weights, before, after):
    jobs = list(range(len(processing_times)))
    new_before = copy.deepcopy(before)
    new_after = copy.deepcopy(after)
    change = True

    while change:
        change = False
        for i in jobs:
            for j in jobs:
                if i != j and i not in new_before[j] and not has_path(j, i, new_after):
                    tmp_before = copy.deepcopy(new_before)
                    tmp_before[j].add(i)
                    path_length = compute_longest_path(jobs, tmp_before)
                    gamma = [
                        (path_length[k, l], (k, l))
                        for k in (before[i] - new_before[j]) | set([i])
                        for l in (after[j] - new_after[i]) | set([j])
                    ]
                    pairs = [(k, l) for _, (k, l) in sorted(gamma, reverse=True)]
                    tmp_before, tmp_after = frame1(
                        pairs,
                        processing_times,
                        due_dates,
                        weights,
                        new_before,
                        new_after,
                    )

                    if tmp_before is not None:
                        change = True
                        new_before = tmp_before
                        new_after = tmp_after

    return new_before, new_after


def has_path(i, j, after):
    open = deque([i])
    checked = set()

    while len(open) > 0:
        u = open.popleft()

        for v in after[u]:
            if v == j:
                return True

            if v not in checked:
                checked.add(v)
                open.append(v)

    return False


def compute_longest_path(jobs, before):
    d = {}

    for i in jobs:
        for j in jobs:
            if i in before[j]:
                d[i, j] = -1
            else:
                d[i, j] = 0

    for k in jobs:
        for i in jobs:
            for j in jobs:
                if d[i, j] > d[i, k] + d[k, j]:
                    d[i, j] = d[i, k] + d[k, j]

    return {k: -v for k, v in d.items()}


def frame1(pairs, processing_times, due_dates, weights, before, after):
    new_before = copy.deepcopy(before)
    new_after = copy.deepcopy(after)

    for k, l in pairs:
        if check_kanet_conditions(
            k, l, processing_times, due_dates, weights, new_before, new_after
        ):
            new_before[l].add(k)
            new_after[k].add(l)
        else:
            return None, None

    return new_before, new_after


def check_kanet_conditions(i, j, processing_times, due_dates, weights, before, after):
    jobs = {i for i in range(len(processing_times))}
    p_i = processing_times[i]
    w_i = weights[i]
    d_i = due_dates[i]
    b_i = before[i]
    a_i = after[i]
    a_i_bar = jobs - a_i
    p_j = processing_times[j]
    w_j = weights[j]
    d_j = due_dates[j]
    b_j = before[j]
    a_j = after[j]
    a_j_bar = jobs - a_j

    p_b_j = sum(processing_times[k] for k in b_j)
    p_common = sum(processing_times[k] for k in b_i | b_j) + p_i + p_j

    # K1
    k1_common = (w_i - w_j) * p_common / w_i
    if (
        p_i <= p_j
        and w_i >= w_j
        and (
            d_i
            <= max(
                d_j,
                k1_common + w_j * d_j / w_i,
            )
            or (d_i <= k1_common + w_j * (p_b_j + p_j) / w_i)
        )
    ):
        return True

    p_a_i_bar = sum(processing_times[k] for k in a_i_bar)

    # K2
    k2_common = (w_j - w_i) * p_a_i_bar / w_j
    if (
        p_i <= p_j
        and w_i < w_j
        and d_j >= k2_common + w_i * d_i / w_j
        and d_j
        >= k2_common
        + w_i * (sum(processing_times[k] for k in a_i_bar & a_j_bar) - p_j) / w_j
    ):
        return True

    # K3
    if (
        p_i <= p_j
        and w_i < w_j
        and d_i <= (w_i - w_j) * p_a_i_bar / w_i + w_j * (p_b_j + p_j) / w_i
        and p_i <= (w_i - w_j) * (p_a_i_bar - p_b_j) / w_i + w_j * p_j / w_i
    ):
        return True

    # K4
    if (
        w_i >= w_j
        and d_j >= min(d_i, (w_j - w_i) * p_common / w_j + w_i * d_i / w_j)
        and d_j >= p_a_i_bar - w_i * p_j / w_j
    ):
        return True

    # K5
    if (
        w_i >= w_j
        and d_i <= (w_i - w_j) * p_common / w_i + w_j * (p_b_j + p_j) / w_i
        and p_j >= w_j * (p_a_i_bar - p_b_j - p_j) / w_i
    ):
        return True

    # K6
    if (
        w_i < w_j
        and d_j >= (w_j - w_i) * p_a_i_bar / w_j + w_i * d_i / w_j
        and d_j >= p_a_i_bar - w_i * p_j / w_j
    ):
        return True

    # K7
    if d_j >= p_a_i_bar:
        return True

    return False
