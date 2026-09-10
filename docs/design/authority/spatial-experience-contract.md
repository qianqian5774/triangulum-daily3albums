# Spatial experience contract

Status: **CURRENT PRODUCT SPATIAL CONTRACT**

This contract defines how the approved exterior and interior visual authorities
relate. It specifies product behavior, not a particular implementation tool.

## Storyboard relationship

- The FRAME 01–14 SVG storyboard and the approved visual packages are
  complementary parts of the same authority.
- The storyboard remains authoritative for its detailed written interaction
  notes, state order, HUD behavior, shot intent and FRAME 04–14 interior flow.
- Only the former FRAME 01–03 exterior imagery and shop-materialization sequence
  are replaced. Their current visual realization is the persistent 3D Entry
  Diorama with six named preset views, bounded inspection, and a real entrance door.
- The Record Shop interior production set elaborates the storyboard's FRAME
  04–14 interior appearance; it does not replace the storyboard's interaction
  definitions.

## Exterior arrival state

- The Entry Diorama is the persistent arrival surface and is represented as a
  real three-dimensional scene derived from the frozen exterior package.
- The six named preset views are the composition anchors. Pointer or touch inspection
  and zoom may move only inside the implemented bounded yaw, pitch, and zoom range;
  unbounded orbit, first-person navigation, and arbitrary perspective distortion are
  outside the contract.
- Every approved view must preserve a normal architectural perspective, the
  full square plinth, a complete roof, readable entrance and the same physical
  arrangement. A camera change may reveal a hidden face but may not rearrange
  the store.
- The entrance door is a real, visibly supported part of the model and the
  primary transition target. It must not be represented by an unrelated
  floating hotspot or an invisible full-scene click target.

## Door transition

- Activating the entrance door moves from the exterior arrival state into the
  Record Shop interior state.
- The transition communicates crossing the threshold; it does not imply that
  the exterior shell must reproduce the interior concept floor plan one-for-one.
- During the transition, controls belonging only to exterior model inspection
  cease to be active. Interior controls become available only after the interior
  state is established.
- Returning to the exterior restores the most recently selected approved
  exterior camera view unless the session is intentionally reset.

## Interior state

- The interior is governed by the FRAME 04–14 visual production set, not by a
  free-roaming three-dimensional camera.
- Screen, device, inventory, history, reading and HUD changes are composited
  state transitions over the approved Record Shop interior environment.
- The latest attendant authority is used throughout; the former interior
  attendant is archived and has no authority status.

## Continuity requirements

- Exterior and interior share store identity, material language and landmark
  inventory, while remaining independently composed spaces.
- The door transition is the sole canonical boundary between exterior and
  interior. No former street-approach, shop-materialization or alley sequence is
  part of the current contract.
- Neither camera motion nor transition effects may introduce new architecture,
  hide defects, alter the square plinth, change character identity or replace
  the approved interior environment.
