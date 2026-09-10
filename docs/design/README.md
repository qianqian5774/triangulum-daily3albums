# Design

Status: **CURRENT**

This directory holds the formal design contract for the deployed Record Shop. Its current Markdown authority documents are version-controlled. It is intentionally limited to the documents required to understand the current spatial model, interaction semantics, and visual acceptance boundary.

## Reading order

1. [Formal design authority](./authority/README.md)
2. [Visual and visual-interaction system](./authority/ui-visual-interaction-system.md)
3. [Interaction specification](./authority/Triangulum-Daily-UI-Interaction-Specification-v1.md)
4. [Product concept](./authority/ui-redesign-concept-v1.md)
5. [Spatial experience contract](./authority/spatial-experience-contract.md)

The production source and shipped assets remain the implementation evidence: Entry Diorama lives under ui/src/components/record-shop, the interior scene and its layered assets are under ui/src/components/record-shop and ui/src/assets/record-shop, and RecordShopRoute connects them to published data.

Historical design explorations, rejected directions, and prompt iterations do not belong in this authority set. They may remain in local archival material for provenance, but they cannot override current source or these documents.
