> **Historical / superseded:** this local prototype plan predates the current production Record Shop. The current authority is [docs/design/](../design/), while source controls deployed behavior.

# UI-RD-04: physical record-shop interaction plan

Date: 2026-08-09. Status: local prototype implementation plan only. This plan is bounded
by `ui-redesign-concept-v1.md`, `Triangulum-Daily-UI-Interaction-Specification-v1.md` and
`ui-visual-interaction-system-v1.md`; it cannot choose or
replace the product model.

## Non-negotiable product chain

`ordinary street -> impossible record shop appears -> cross the door -> credible shop
interior -> a real shop fixture activates -> adjacent sleeves become browsable -> one
sleeve is extracted -> that sleeve is read in Treatment -> it returns to its former place`

Today and Archive are inventory states for this one chain. They are never independent
navigation models. The daily inventory contains one, two, or three unlocked **BJT slot
groups**, each containing exactly three physical-looking record sleeves. The active group
is browsed horizontally; vertical movement changes the active BJT slot. Six or nine
unlocked sleeves must never flatten into one horizontal stream, numbered system, date
ledger, service rail, card list, or 3x3 wall.

## Current prototype boundary

The existing `/record-shop` prototype remains useful evidence for real-data/file-build
isolation, street-to-shop continuity, DOM sleeve identity, Treatment return, keyboard,
touch and reduced-motion behavior. Its currently implemented flattened nine-sleeve
horizontal browsing state is superseded by this plan and must not be used as future design
or interaction authority. The next prototype iteration must retain those independent
engineering capabilities while replacing only that browse structure with BJT slot groups.

## Research conclusions applied to the prototype

- The two *Music Collection Browsing Concept* studies explicitly describe obvious album
  gestures and a real record-bin browsing metaphor. They are the core interaction
  prototype: a centred sleeve is legible, while neighbouring sleeves remain visibly
  adjacent and reachable. [Kiut](https://dribbble.com/shots/5827508-Music-collection-browsing-concept),
  [Andre Navarre](https://dribbble.com/shots/5953384-Music-collection-browsing-concept)
- A finite native horizontal scroller is the robust basis **within the active three-record
  slot**: `scroll-snap-align: center` supplies an unambiguous resting sleeve, and
  transformations belong on the cover child so scroll distance remains stable.
  [Scroll-driven Cover Flow technical explanation](https://scroll-driven-animations.style/demos/cover-flow/css/)
- Perspective is a spatial cue, not a product model. The CSS baseline gives a central
  sleeve a frontal plane and neighbours angled, narrower planes; there is no infinite loop
  or floating generic carousel. [Addy Osmani's implementation analysis](https://addyosmani.com/blog/coverflow/)
- The shop is a reason for the object, never a detached 3D navigational game. The record
  crate is a physical fixture that expands out from a counter/shelf sightline, borrowing
  only the object-led causal relationship from the Coke Studio store case.
  [UNIT9 case](https://www.unit9.com/project/coke-studio-real-magic-virtual-record-store)
- Treatment is a continuation of the selected sleeve: capture the source bounds, hold the
  shop in view as spatial evidence, move the labelled sleeve to the reading position, then
  reverse it. FLIP is a future enhancement for this measured DOM transition, not a
  prerequisite; its documented state capture/reconcile model fits this boundary.
  [GSAP Flip documentation](https://gsap.com/docs/v3/Plugins/Flip/)
- Codrops' 3D carousel and content/image transition sources confirm that scroll-led depth
  and object-to-content movement are possible Web techniques. They are used only for
  implementation lessons, not as a substitute product direction.
  [3DCarousel](https://github.com/codrops/3DCarousel/),
  [ContentLayoutTransition](https://github.com/codrops/ContentLayoutTransition),
  [ImageToContent](https://github.com/codrops/ImageToContent),
  [ImageToGridTransition](https://github.com/codrops/ImageToGridTransition)

No reference code is copied. The GSAP infinite-loop example is deliberately rejected for
a daily issue: 3/6/9 is a finite release-aware inventory, but its actual adjacent positions
are preserved inside three-record BJT slot groups rather than a flattened six- or nine-record
strip.

## Prototype A: in-store physical browsing

The visitor faces a counter-height **listening crate** that is visibly part of the shop:
wood front, shelf labels, a turntable/lamp edge, sleeves sitting within the crate, and a
seen attendant behind it. The crate front folds down and its sleeves rise as a single
activation. This is a chosen spatial bridge, not a second information system.

The crate exposes one active BJT slot group containing exactly three sleeves. Its horizontal
finite, snap-centred strip lets the current sleeve face the visitor with visible
side/thickness, while immediate left/right neighbours angle away, overlap slightly, and
remain partly readable. Horizontal wheel/trackpad motion, touch, mouse drag, left/right
keys, Home/End, and explicit previous/next controls move only within that three-record
group. A distinct vertical control or gesture changes between unlocked 08:00, 12:30 and
16:00 groups while preserving the same crate, shop and focused-object context. First
activation brings a sleeve to focus; activation of that focused sleeve extracts it.

Treatment keeps the shop's counter, shelf light and attendant silhouette behind a changed
camera/readability field. It retains the selected record identifier and cover while it
moves from its exact source bounds into the foreground. Closing reverses the same path and
restores focus to the source sleeve. In reduced motion, it changes state immediately but
keeps the same source/target identity and return focus.

## Prototype B: exterior-to-interior transition

The exterior is a full responsive street composition, not two cropped flanks. Its semantic
anchors are: street horizon, central building relationship, impossible storefront sign,
door, and interior light. Sky, pavement, trees, and peripheral facades are separately
expandable layers. The scene begins ordinary; attention reveals the storefront's light and
sign; the door opens; the camera crosses the threshold into the shop; the visitor settles
long enough to see counter, sleeves, furniture, and attendant before the crate activates.

## Motion storyboard

| Beat | Cause and visible effect | Baseline technology |
| --- | --- | --- |
| anomaly | a reflection/light rhythm locates the missing storefront | CSS opacity, light and transform |
| approach | the door and sign become the only converging central anchors | CSS transform/scale; no fake scroll scene |
| threshold | door opens, doorway grows, exterior layers recede | staged CSS transitions with semantic scene state |
| arrival | interior resolves; counter, shelves and attendant hold still briefly | DOM layers, no forced camera control |
| crate activation | attendant/environment responds and the physical crate opens | DOM class state, staggered sleeve rise |
| slot change | visitor moves vertically between unlocked BJT slot groups; the crate re-stages its three sleeves | DOM state plus CSS/GSAP layer transition; preserve fixture and focused identity |
| browse | horizontal input shifts the active three-record native scroll position; child covers tilt by offset | Scroll Snap plus calculated child transforms |
| focus | one sleeve becomes frontal, closer and topmost | CSS transform/z-index, stable scroll slots |
| extraction | focused sleeve travels from its measured source rectangle to Treatment | DOM FLIP-style fixed flying sleeve |
| return | the same sleeve travels back and receives focus | reverse measured travel and focus restoration |

## Responsive and asset direction

The final art is not generated until these two prototypes pass browser inspection. It will
be layer-first: street sky/pavement, left and right expandable facades, central storefront,
door/light layer, interior architecture, counter/crate, shelf stock, attendant foreground,
and transient light/shadow layers. No full background image may encode the interaction
layout. On mobile, the full storefront remains visible before entry; in the shop, one large
sleeve with partial neighbours remains the active three-record group rather than a
single-card page. Vertical slot switching remains available on every supported viewport.
On ultrawide displays, peripheral street/stock expands while the storefront, crate, and
focused sleeve retain capped readable dimensions.

## Engineering boundaries

The prototypes use the public Today contract, real covers, BJT 08:00/12:30/16:00
availability, and an embedded `file://` data path. Production code receives a null local
alias, so neither prototype becomes a deployed route or a visitor-side data API. Archive
will replace the issue inventory in this same slot-group fixture: vertical slot selection
and horizontal three-record browsing remain identical for a selected historical date.
Keyboard, touch, cover fallback, and reduced-motion behavior are acceptance requirements.
