# Examples Action Specification

## Objective

Provide concise, teachable Android examples for students and instructors.

## Primary Use Cases

### Student

A student asks for an example to understand a concept.

### Instructor

An instructor requests an example to use while explaining a topic in class.

## Example Types

The action SHALL support:

- basic example;
- intermediate example;
- advanced example;
- common mistake;
- corrected example;
- teaching example;
- exercise derived from an example (optional, generated through the practice
  prompt structure).

## Example Output

```text
/examples ViewModel

Concept
ViewModel separates presentation state and logic
from the UI lifecycle.

Basic example
...

Common mistake
...

Teaching question
What state belongs in the ViewModel?

Advanced example
...
```

## Instructor Mode

The architecture SHALL allow a future `--teacher` flag without a separate agent
(RQ-EX-011). Teacher output adds teaching questions and classroom discussion
points.

## Important Principle

Examples SHALL be small enough to explain during a lesson and SHALL identify the
concept being demonstrated. Examples SHALL be independent from the student's
project unless project context is explicitly requested (RQ-EX-008).

## Knowledge Organization

Curated examples and the topic taxonomy live under:

```text
knowledge/
├── kotlin/
├── compose/
├── architecture/
├── android/
└── testing/
```

Curated examples may coexist with generated examples.