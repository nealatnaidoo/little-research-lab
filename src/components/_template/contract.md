# Component Contract Template (v4)

## COMPONENT_ID

C#-{ComponentName}

## PURPOSE

{Brief description of what this component does}

## INPUTS

- `{InputName}`: {Description}

## OUTPUTS

- `{OutputName}`: {Description}

## DEPENDENCIES (PORTS)

- `{PortName}`: {Description of port usage}

## SIDE EFFECTS

- {Description of I/O, database writes, cache invalidation, etc.}

## INVARIANTS

- I1: {Invariant that must always hold}
- I2: {Another invariant}

## ERROR SEMANTICS

- {How errors are handled - returns in output vs throws}

## RULES DEPENDENCIES

- Section: `{rules_section}`
- Keys: `{specific_keys_used}`

## SPEC REFS

- Epics: {E#.#}
- Test Assertions: {TA-E#.#-##}
- Regression Invariants: {R#}

## FC (Functional Core)

Pure functions with no I/O:

- `{function_name}(input) -> output`: {Description}

## IS (Imperative Shell)

I/O handlers and adapters:

- `{handler_name}`: {Description}

## TESTS

- `tests/unit/test_{component}.py`: {Test descriptions}
- Test Assertions: {TA-###}

## EVIDENCE

- `artifacts/{evidence_file}.json`
