"""
Component Template (v4)

This template defines the atomic component structure for creator-publisher-v4.

Directory structure:
- contract.md  - Component contract (ports, DTOs, invariants)
- fc/          - Functional Core (pure logic, no I/O)
- is/          - Imperative Shell (handlers, adapters)
- tests/       - Unit and integration tests

Usage:
1. Copy this template to src/components/C#-{Name}/
2. Update contract.md with component-specific details
3. Implement FC functions first (TDD)
4. Implement IS handlers that orchestrate FC with I/O
5. Add manifest entry to manifests/component_manifest.json
"""
