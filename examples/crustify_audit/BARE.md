# Ablation: the bare backend

`crustify audit <workdir> <TASK> --task-only` starts the orchestrator's backend CLI
with the task file, here `TASK-bare.md.template`, as its **entire** prompt: no
orchestrator role, no conventions, no skill index.

`TASK-bare.md.template` is deliberately minimal -- two lines, 21 words.

## Running it

    docker run -d --name bare-git2 \
        -e OPENROUTER_API_KEY \
        -v /path/to/target:/target \
        -v /path/to/TASK-bare.md:/campaign/TASK.md:ro \
        -v bare-git2-work:/work \
        crustify
    docker exec -it bare-git2 \
        crustify audit /target /campaign/TASK.md --task-only \
        --model openrouter/anthropic/claude-opus-5 --billing api

Nothing spawns auditors in bare mode, so there is no per-auditor budget: the run
takes whatever the single agent takes. Cap it from outside if you need one.
