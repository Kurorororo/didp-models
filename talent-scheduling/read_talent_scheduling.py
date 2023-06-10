def read(filename):
    with open(filename) as f:
        values = f.read().split()

    name = values[0]
    n_scenes = int(values[1])
    n_actors = int(values[2])
    position = 3
    actor_to_scenes = [[0 for _ in range(n_scenes)] for _ in range(n_actors)]
    actor_to_cost = [0 for _ in range(n_actors)]

    for i in range(n_actors):
        for j in range(n_scenes):
            value = int(values[position])
            actor_to_scenes[i][j] = value
            position += 1
        actor_to_cost[i] = int(values[position])
        position += 1

    scene_to_duration = [0 for _ in range(n_scenes)]

    for i in range(n_scenes):
        scene_to_duration[i] = int(values[position])
        position += 1

    return name, actor_to_scenes, actor_to_cost, scene_to_duration


def compute_solution_cost(solution, actor_to_scenes, actor_to_cost, scene_to_duration):
    n_actors = len(actor_to_scenes)
    n_scenes = len(scene_to_duration)
    scene_to_actors = [
        [j for j in range(n_actors) if actor_to_scenes[j][i] == 1]
        for i in range(n_scenes)
    ]
    cost = 0
    on_location = set()

    for i, s in enumerate(solution):
        for j in scene_to_actors[s]:
            if j not in on_location:
                on_location.add(j)

        cost += scene_to_duration[s] * sum(actor_to_cost[j] for j in on_location)

        for j in scene_to_actors[s]:
            if sum(actor_to_scenes[j][k] for k in solution[i + 1 :]) == 0:
                on_location.remove(j)

    return cost


def validate(solution, cost, actor_to_scenes, actor_to_cost, scene_to_duration):
    actual_cost = compute_solution_cost(
        solution, actor_to_scenes, actor_to_cost, scene_to_duration
    )
    if cost != actual_cost:
        print(
            "The cost {} of solution mismatches the actual cost {}".format(
                cost, actual_cost
            )
        )
        return False

    return True


def compute_base_costs(actor_to_scenes, actor_to_cost, scene_to_duration):
    n_scenes = len(scene_to_duration)
    n_actors = len(actor_to_scenes)
    scene_to_base_cost = [
        scene_to_duration[i]
        * sum(actor_to_cost[j] for j in range(n_actors) if actor_to_scenes[j][i] == 1)
        for i in range(n_scenes)
    ]
    return scene_to_base_cost


def add_base_costs(solution, cost, scene_to_base_cost):
    for i in solution:
        cost += scene_to_base_cost[i]
    return cost


def simplify(actor_to_scenes, actor_to_cost, scene_to_duration):
    single_actor_cost = 0
    old_actor_to_scenes = actor_to_scenes
    old_actor_to_cost = actor_to_cost
    old_scene_to_duration = scene_to_duration
    scene_to_new_scene = list(range(len(scene_to_duration)))
    while True:
        (
            new_actor_to_scenes,
            new_actor_to_cost,
            new_single_actor_cost,
        ) = eliminate_single_scene_actors(
            old_actor_to_scenes, old_actor_to_cost, scene_to_duration
        )
        (
            new_actor_to_scenes,
            new_scene_to_duration,
            new_scene_to_new_scene,
        ) = concatenate_duplicate_scenes(new_actor_to_scenes, old_scene_to_duration)

        if (
            new_actor_to_scenes == old_actor_to_scenes
            and new_actor_to_cost == old_actor_to_cost
            and new_scene_to_duration == old_scene_to_duration
        ):
            scene_to_original = [[] for _ in range(len(new_scene_to_duration))]
            for i, j in enumerate(scene_to_new_scene):
                scene_to_original[j].append(i)

            return (
                new_actor_to_scenes,
                new_actor_to_cost,
                new_scene_to_duration,
                single_actor_cost,
                scene_to_original,
            )

        for i in scene_to_new_scene:
            scene_to_new_scene[i] = new_scene_to_new_scene[scene_to_new_scene[i]]

        old_actor_to_scenes = new_actor_to_scenes
        old_actor_to_cost = new_actor_to_cost
        old_scene_to_duration = new_scene_to_duration
        single_actor_cost += new_single_actor_cost


def eliminate_single_scene_actors(actor_to_scenes, actor_to_cost, scene_to_duration):
    single_actor_cost = 0
    keep = []
    for i, scenes in enumerate(actor_to_scenes):
        if sum(scenes) > 1:
            keep.append(i)
        else:
            for j, v in enumerate(scenes):
                if v == 1:
                    single_actor_cost += scene_to_duration[j] * actor_to_cost[i]

    new_actor_to_scenes = [actor_to_scenes[i].copy() for i in keep]
    new_actor_to_cost = [actor_to_cost[i] for i in keep]

    return new_actor_to_scenes, new_actor_to_cost, single_actor_cost


def concatenate_duplicate_scenes(actor_to_scenes, scene_to_duration):
    n_actors = len(actor_to_scenes)
    n_scenes = len(scene_to_duration)
    scene_to_new_scene = list(range(n_scenes))
    scene_to_actors = [
        [j for j in range(n_actors) if actor_to_scenes[j][i] == 1]
        for i in range(n_scenes)
    ]

    scene_to_duplicates = [[] for _ in range(n_scenes)]
    checked = set()

    index = 0

    for i in range(n_scenes):
        if i in checked:
            continue
        scene_to_new_scene[i] = index
        for j in range(i + 1, n_scenes):
            if scene_to_actors[i] == scene_to_actors[j]:
                scene_to_duplicates[i].append(j)
                scene_to_new_scene[j] = index
                checked.add(j)
        index += 1

    new_actor_to_scenes = [
        [actor_to_scenes[i][j] for j in range(n_scenes) if j not in checked]
        for i in range(n_actors)
    ]
    new_scene_to_duration = [
        scene_to_duration[i]
        + sum([scene_to_duration[j] for j in scene_to_duplicates[i]])
        for i in range(n_scenes)
        if i not in checked
    ]

    return new_actor_to_scenes, new_scene_to_duration, scene_to_new_scene


def reconstruct_solution(solution, cost, single_actor_cost, scene_to_original):
    new_solution = []
    for i in solution:
        new_solution += scene_to_original[i]
    return new_solution, cost + single_actor_cost
