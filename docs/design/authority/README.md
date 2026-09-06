# Formal design authority

Status: **CURRENT**

This directory defines the current product experience and visual acceptance boundary for Triangulum Daily. It does not override runtime data, public JSON, BJT clock behavior, or the GitHub Pages architecture; those remain governed by current source, tests, workflow, and Foundation documentation.

## Documents

- [Visual and visual-interaction system](./ui-visual-interaction-system.md): visual world, material relationships, composition, interaction hierarchy, responsive behavior, and visual acceptance.
- [Interaction specification](./Triangulum-Daily-UI-Interaction-Specification-v1.md): entry, BJT availability, Daily Device session states, input, transitions, return behavior, and accessibility.
- [Product concept](./ui-redesign-concept-v1.md): product intent, Record Shop metaphor, and explicitly rejected product directions.
- [Spatial experience contract](./spatial-experience-contract.md): relationship between the Entry Diorama, physical door, and Record Shop interior.

## Implementation evidence

- Entry Diorama: ui/src/components/record-shop/EntryDiorama.tsx and its diorama modules.
- Formal interior composition: ui/src/components/record-shop/InteriorGallery.tsx and ui/src/assets/record-shop/formal/.
- Production route and public-data integration: ui/src/routes/RecordShop.tsx and ui/src/components/record-shop/catalog.ts.

A visual assertion that conflicts with the currently deployed implementation must be reviewed and corrected here rather than silently treated as a new code requirement.
