# Visual Environment Specification

This document records Selina's requested appearance for the sidewalk robot simulation. Use it as the visual target when continuing the environment work. The earlier two-block preview is superseded by the four-block layout. Exact pixel dimensions, colors, and building counts in the current code are implementation choices, not extra requirements from Selina.

## View and movement surfaces

- Show the environment from an aerial, top-down view. The viewer sees building rooftops, roads, and sidewalks.
- The robot cannot enter buildings or travel on ordinary road cells. It stays on sidewalks and may use marked crosswalks to reach the other blocks.
- Keep movement on square grid cells even though the sidewalks have a curved visual appearance.

## Four-block layout

- Show **four blocks in a 2-by-2 arrangement** around one central road intersection. Do not show additional blocks or scenery beyond these four for now.
- Make each block a **long rectangle**, with its long side running left to right. The four blocks should have approximately matching proportions.
- Show **multiple buildings from above**, rather than one building filling each block. Selina has not set an exact number or arrangement of buildings.
- Sidewalks surround the buildings and curve visually around the block corners.
- Sidewalks are **two grid squares wide**. Roads are **twice that width: four grid squares**.

## Intersection and road paint

- Let the roads form a four-way intersection between the blocks. Keep the **middle of the intersection unpainted**: no centerline, crosswalk stripe, or stop bar through its center.
- Place **white, walkable crosswalks**: four across the road approaches immediately around the intersection, plus **four more where each road ends at the edge of the map**, where the sidewalk curbs are visible. Each connects the two sidewalks it joins. Selina described the crosswalks as “parallel to the blocks it connects.” In the supplied reference image, the top and bottom crossings have vertical white bars; the left and right crossings have horizontal white bars. Follow that orientation for all eight, so the top-end and bottom-end crossings have vertical bars and the left-end and right-end crossings have horizontal bars.
- Put a **solid white stop line before each crosswalk** on the approaching lane. Draw a **white dashed centerline** along each road between its two crossings, ending before their stop lines. Resume the centerline on the opposite approach; do not carry it across the unpainted intersection.
- Use **no yellow road lines and no text overlaid on the scene**, including “STOP” labels or stock watermarks. The reference image was supplied for layout and marking placement; its yellow bars and labels are not part of the desired scene.

## Style reference and colors

[`reference/generated_city_blocks.png`](reference/generated_city_blocks.png) is the supplied reference image. Match its style, not its extent: peach sidewalks with faint paving joints and a raised lip, dark asphalt, and buildings made of several stepped rooftop volumes with small rooftop details and drop shadows. Buildings here are all grey; the reference's bright accent buildings, tree median, and extra crossings belong to a larger map and are not part of this scene.

## Details Selina has not fixed

The exact grid size, tile size, roof colors, number of buildings per block, building spacing, curve radius, tree or grass treatment, stripe spacing, and robot start cell may be chosen during implementation. Keep the proportions and road-marking relationships above. Document any chosen values alongside the code.

## Current implementation context

[`sim/scene.py`](../sim/scene.py) (map data) and [`sim/render.py`](../sim/render.py) (drawing) are the current four-block preview. They use 36 by 24 cells and 28-pixel tiles, with six or seven stepped rooftop volumes per block (listed in `BLOCK_LAYOUTS`) and eight crosswalks. The static background is drawn once at 3x resolution and scaled down for smooth edges. Those values can change while preserving this visual specification. Edit these files in place; Git keeps the history.
