# Automated Avatar Image Tagging Workflow

This document describes the fully automated process for analyzing and tagging avatar images in PyAgentVox. This workflow can be executed "in one shot with no human in the loop."

## Overview

The avatar tag system requires each image to be registered in `pyagentvox.yaml` with:
- **Path**: Relative to avatar directory
- **Description**: One-line summary of what the character is doing/wearing/expressing
- **Tags**: Multi-dimensional tags including emotion, outfit, pose, and context

## Automated Tagging Process

### Prerequisites

1. **Background removal completed**: All images should have transparent backgrounds (use `remove_backgrounds_batch.py`)
2. **Avatar directory configured**: Images are in `~/.claude/luna/` or configured directory
3. **Team support enabled**: Claude Code must support team/agent spawning

### Step 1: Create Tagging Team

```python
# Create a team for parallel image analysis
TeamCreate(
    team_name="image-tagging",
    description="Analyze avatar images and generate descriptions + tag lists",
    agent_type="team-lead"
)
```

### Step 2: Count and Distribute Images

```bash
# Get all images (excluding controls and backups)
find ~/.claude/luna -name "*.png" -type f | grep -v "controls/" | grep -v "bkp/" | sort

# Calculate batches (aim for 4 agents, ~55 images each for 221 total)
# Batch 1: Images 1-55
# Batch 2: Images 56-110
# Batch 3: Images 111-165
# Batch 4: Images 166-221
```

### Step 3: Create Analysis Tasks

Create 4 tasks for parallel analysis:

```python
TaskCreate(
    subject="Analyze batch 1 (images 1-55) and generate tag lists",
    description="""
    Analyze images from <first> to <last> (first 55 images alphabetically).

    For each image:
    1. View the image using Read tool
    2. Generate a one-line description
    3. Create a tag list with:
       - **Required**: At least 1 emotion tag
       - **Outfit tags**: Describe clothing
       - **Pose tags**: Describe gesture/action
       - **Context tags**: Additional context

    Save results to: C:/Users/{user}/.claude/tasks/image-tagging/batch1_results.txt
    """,
    activeForm="Analyzing batch 1 images"
)

# Repeat for batches 2, 3, and 4
```

### Step 4: Spawn Analysis Agents

Spawn 4 general-purpose agents, one per batch:

```python
Task(
    subagent_type="general-purpose",
    team_name="image-tagging",
    name=f"batch{n}-analyzer",
    prompt=f"""
    You are analyzing batch {n} of avatar images.

    Your task:
    1. Get the full list of images in ~/.claude/luna (excluding controls/ and bkp/)
    2. Sort them alphabetically
    3. Take images {start}-{end} from that sorted list
    4. For each image:
       - Use Read tool to view the image
       - Write a one-line description
       - Generate appropriate tags
    5. Save results in YAML format

    Format:
    ```yaml
    images:
      - path: "filename.png"
        description: "One-line description"
        tags: ["emotion", "outfit", "pose", "context"]
    ```

    When done, mark task #{n} as completed.
    """
)
```

### Step 5: Create Consolidation Task

Create a task that waits for all batches to complete:

```python
TaskCreate(
    subject="Consolidate all batch results into pyagentvox.yaml",
    description="""
    After all 4 batch analyzers complete:
    1. Read the 4 result files
    2. Merge all image entries into a single list
    3. Update pyagentvox.yaml with all analyzed images
    4. Generate summary report
    """,
    activeForm="Consolidating results into config"
)

# Block this task until all 4 batches complete
TaskUpdate(taskId=9, addBlockedBy=["1", "2", "3", "4"])
```

## Tag Guidelines for Agents

### Emotion Tags (Required - At Least One)

Standard emotions from PyAgentVox system:
- `cheerful` - Happy, smiling, positive
- `excited` - Very enthusiastic, energetic
- `calm` - Peaceful, relaxed, serene
- `focused` - Concentrating, serious, working
- `warm` - Affectionate, caring, gentle
- `empathetic` - Understanding, compassionate
- `neutral` - No strong emotion, baseline
- `playful` - Fun, teasing, lighthearted
- `surprised` - Shocked, amazed, unexpected
- `curious` - Interested, investigating
- `determined` - Resolute, committed

### Outfit Tags

Describe what the character is wearing:
- `dress` - Any dress (specify style if notable)
- `cream-dress` - Specific cream-colored dress
- `hoodie` - Hooded sweatshirt/casual
- `daisy-dukes` - Short denim shorts
- `casual` - Everyday clothing
- `formal` - Professional/fancy attire
- `pajamas` - Sleepwear
- `costume` - Special outfit (specify: pirate, ninja, etc.)
- `swimwear` - Beach/pool attire

### Pose Tags

Describe the gesture or action:
- `wave` - Waving hello/goodbye
- `peace-sign` - Peace/victory sign with fingers
- `thumbs-up` - Approval gesture
- `victory` - Victory pose (both arms up)
- `typing` - Working on keyboard
- `coffee` - Holding/drinking coffee
- `salute` - Military-style salute
- `wink` - Winking one eye
- `shrug` - Shoulder shrug gesture
- `pointing` - Pointing at something
- `crossed-arms` - Arms crossed

### Context Tags

Additional situational context:
- `summer` - Summery/warm weather vibe
- `coding` - Programming/development context
- `celebration` - Celebrating success
- `relaxed` - Laid-back situation
- `working` - Actively working
- `listening` - Paying attention
- `thinking` - Deep in thought
- `laptop` - Using computer

## Expected Output Format

Each batch result file should contain YAML:

```yaml
images:
  - path: "cheerful-wave.png"
    description: "Luna in cream dress, waving cheerfully with a bright smile"
    tags: ["cheerful", "cream-dress", "wave", "friendly"]

  - path: "focused-laptop.png"
    description: "Luna in hoodie, focused on laptop while typing"
    tags: ["focused", "hoodie", "typing", "coding", "laptop"]

  - path: "excited-victory.png"
    description: "Luna in casual outfit, arms raised in excited victory pose"
    tags: ["excited", "casual", "victory", "celebration"]
```

## Final Config Structure

After consolidation, `pyagentvox.yaml` should contain:

```yaml
avatar:
  directory: "~/.claude/luna"
  default_size: 300
  cycle_interval: 4000

  filters:
    include_tags: []
    exclude_tags: []
    require_all_include: false

  animation:
    flip_threshold: 0.5
    flip_duration: 300
    flip_steps: 15

  images:
    - path: "ah-ha.png"
      description: "Description here"
      tags: ["emotion", "outfit", "pose", "context"]

    # ... all 221 images ...

    - path: "yawn.png"
      description: "Description here"
      tags: ["emotion", "outfit", "pose"]
```

## Verification Steps

After consolidation completes:

1. **Count check**: Verify all 221 images are in config
   ```bash
   python -c "import yaml; print(len(yaml.safe_load(open('pyagentvox.yaml'))['avatar']['images']))"
   ```

2. **Tag validation**: Ensure every image has at least one emotion tag
   ```bash
   python -m pyagentvox.avatar_tags list
   ```

3. **Emotion distribution**: Check variety of emotions used
   ```bash
   python -m pyagentvox.avatar_tags list --tag cheerful
   python -m pyagentvox.avatar_tags list --tag focused
   # etc.
   ```

4. **Test filtering**: Try various tag filters
   ```bash
   python -m pyagentvox --avatar --include-tags daisy-dukes
   python -m pyagentvox --avatar --include-tags hoodie,coding
   python -m pyagentvox --avatar --exclude-tags formal
   ```

## Troubleshooting

### Agent Timeout or Failure

If an agent fails or times out:
1. Check which task is blocked: `TaskList`
2. Manually analyze remaining images in that batch
3. Save results to the expected batch file
4. Mark task as completed: `TaskUpdate(taskId=N, status="completed")`

### Missing Images

If some images are missing from results:
1. Check batch result files for gaps
2. Identify missing images by comparing with directory listing
3. Manually analyze missing images
4. Append to appropriate batch result file

### Tag Validation Errors

If images fail validation (missing emotion tag):
1. Check error message for problematic image path
2. Add emotion tag to that image's tag list
3. Re-save config

## One-Shot Execution

To run this entire process automatically:

```bash
# 1. Ensure images have transparent backgrounds
python remove_backgrounds_batch.py

# 2. Run automated tagging (this workflow)
# [Team creation and agent spawning handled by Claude Code]

# 3. Wait for completion
# [Agents work in parallel, consolidation happens automatically]

# 4. Verify results
python -m pyagentvox.avatar_tags list | wc -l  # Should show 221
```

The entire process should complete in 10-20 minutes depending on agent speed.

## Summary

This automated workflow:
- ✅ Analyzes all images in parallel (4 agents)
- ✅ Generates human-readable descriptions
- ✅ Creates multi-dimensional tag lists
- ✅ Validates emotion tag requirements
- ✅ Consolidates results into config
- ✅ Provides verification and summary
- ✅ **Can run with no human in the loop**

The team-based approach scales to any number of images by adjusting batch sizes and agent count.
