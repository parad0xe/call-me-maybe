_This project has been created as part of the 42 curriculum by nlallema_

## Table of contents

- [Description](#description)
- [Usage](#usage)
- [File formats](#file-formats)
- [Algorithm](#algorithm)
- [Design decisions](#design-decisions)
- [Performance analysis](#performance-analysis)
- [Challenges faced](#challenges-faced)
- [Testing strategy](#testing-strategy)
- [Resources](#resources)

## Description

**Call-me-maybe** is a command-line tool designed to translate natural language queries into structured JSON function calls. The project utilizes the Qwen3-0.6B model and relies on a robust architecture ensuring that the output strictly adheres to defined schemas, even with a small-scale language model.

## Usage

### Installation

Install dependencies and environment via uv:
```bash
make install
```

### Execution

By default, the program processes files in `data/input/` and writes to `data/output/`:
```bash
make run [ARGS="..."]
```

> This command automatically triggers `make install` to ensure the environment is ready.

#### Arguments & Options

| Argument / Flag | Description |
|-----------------|-------------|
| --functions_definition | path to function definitions (default: data/input/functions_definition.json) (format: json) |
| --input | path to user prompts (default: data/input/function_calling_tests.json) (format: json) |
| --output | output file path for results (default: data/output/function_calls.json) (format: json) |
| -t, --timeout | inference time limit in ms (default: 20000) |
| -v, -vv | log verbosity levels (INFO or DEBUG levels) |
| -S, --stop-on-first-error | halt execution immediately upon the first processing error |
| --help, -h | show the help message and exit |

#### Development commands

| Command | Description |
|---------|-------------|
| make clean | remove temporary files and project caches |
| make cache-clean | specifically clear local project caches (e.g., mypy, \_\_pycache__) |
| make lint | check code against flake8 and mypy standards |
| make lint-strict | execute strict linting using mypy --strict |
| make debug | run the program using the Python built-in debugger |

## File Formats

The program relies on structured JSON files to configure the model capabilities and define the tasks to process.

### Function definitions (`functions_definition.json`)

This file contains a list of objects defining the tools available to the LLM. Each object must follow this schema:

- `name` (string): The unique identifier of the function (e.g., `fn_add_numbers`).
- `description` (string): A textual explanation used by the model to determine when to call this function.
- `parameters` (object): A dictionary where each key is an argument name and each value is an object containing a `type` field (accepted values: `string`, `number`, `bool`).
- `returns` (object): An object containing a `type` field defining the return format.

**Example:**

```json
[
  {
    "name": "fn_get_weather",
    "description": "Get the current temperature in a city.",
    "parameters": {
      "city": { "type": "string" },
      "units": { "type": "string" }
    },
    "returns": { "type": "string" }
  }
]
```

### Input prompts (`function_calling_tests.json`)

This file lists the natural language requests that the system must process.

- `prompt` (string): The user query.

**Example:**

```json
[
  { "prompt": "What is the weather in Paris?" },
  { "prompt": "Calculate the sum of 10 and 5." }
]
```

### Output results (`function_calls.json`)

The generated file contains structured function calls resulting from inference. Each entry includes the original prompt along with the extracted data:

- `prompt` (string): The original query.
- `name` (string): The identified function name.
- `parameters` (object): The extracted arguments with correct types.

**Example:**

```json
[
  {
    "prompt": "What is the weather in Paris?",
    "name": "fn_get_weather",
    "parameters": {
      "city": "Paris",
      "units": "celsius"
    }
  }
]
```

> **Note:** All files are validated at load time. If a required field is missing or a type is incorrect, the program raises a `SchemaValidationError`.

## Algorithm

The implementation is based on an inference loop controlled by dynamic syntax constraints:
- **Regex pattern generation:** A regex pattern is dynamically built for each function. It defines the expected JSON structure, including parameter types such as string, number, and bool.
- **Constrained inference:** During token-by-token generation, the system decodes candidate tokens and verifies if they partially match the regex pattern.
- **Logits filtering:** Only tokens that maintain a valid JSON structure according to the function schema are kept. If a token breaks the expected syntax or type, it is ignored in favor of the next most probable candidate.
- **Fallback management:** An internal function `fn_not_implemented` is systematically injected to allow the model to report queries that do not match any known definition.

## Design decisions

- **Pydantic for data integrity:** Every internal data structure — including command-line settings, function definitions, and user prompts — is implemented using Pydantic `BaseModel`. The use of `extra="forbid"` and `frozen=True` ensures strict schema compliance and prevents silent data corruption throughout the inference pipeline.

- **Two-Stage inference pipeline:** To optimize accuracy on the 0.6B parameter model, the process is split into two specialized passes:
  - **Function identification:** A first pass matches the user prompt against available function descriptions to select the correct name.
  - **Parameter extraction:** A second targeted pass focuses exclusively on extracting and typing the arguments required by the identified schema.

- **Constrained decoding via regex:** Instead of relying on model spontaneity, the system uses dynamic regex patterns to filter logits. This guarantees that every generated token contributes to a syntactically valid JSON object that matches the function's signature.

- **Strict inference timeout:** A millisecond timer monitors each inference cycle against the user-defined `--timeout` to prevent infinite loops or stalled processing on ambiguous prompts.

- **Granular error domain isolation:** The application separates concerns through a custom exception hierarchy:
  - **StorageError:** Handles filesystem issues such as permissions or missing files.
  - **SchemaError:** Manages data integrity issues, including invalid JSON structures or Pydantic validation failures.

## Performance analysis

- **Deterministic type coercion:** The system achieves typing reliability by using a formatting engine that injects specialized regex placeholders into the generation process. Rather than hoping for correct formatting, the engine strictly constrains the LLM's output:
  - **Numbers:** Constrained to the pattern `[+-]?(\d{1,15}(\.\d{0,15})?|\.\d{1,15})([eE][+-]?\d{1,15})?`, supporting signed integers, decimal numbers, and scientific notation (e.g., -1.23e+10).
  - **Booleans:** Restricted to the specific tokens `true` or `false`.
  - **Strings:** Enclosed in literal quote boundaries `"[^"\\]*"` to ensure they remain valid JSON primitives.

- **Latency vs. accuracy trade-off:** While constrained decoding adds a slight computational overhead for logit filtering, it guarantees 100% syntactically valid JSON output and reliable function argument typing.

## Challenges faced

- **Real-time token validation (partial inference):** Since LLMs generate text token by token, standard regex matching is insufficient as it only validates complete strings. To address this, the system leverages `regex.fullmatch` with the `partial=True` flag, allowing it to determine whether an intermediate string can still evolve into a valid match. This enables real-time filtering of invalid tokens during generation, ensuring that only candidates compatible with the target pattern are considered.

## Testing Strategy

- **Schema validation:** Compliance testing of Pydantic models using the `extra="forbid"` option to detect any drift or unexpected fields in input data.
- **I/O robustness:** Management of file permissions and automatic directory creation to ensure results are saved safely, even if the target path is missing.
- **Prompt edge cases:** Systematic validation against a variety of input scenarios to ensure stable behavior:
  - **Empty prompts:** Ensuring the pipeline identifies and skips empty input strings to prevent wasted inference cycles.
  - **Ambiguous prompts:** Testing the model's ability to remain within regex constraints even when the natural language intent is unclear.
  - **Unmapped prompts:** Verifying that the `fn_not_implemented` fallback correctly handles requests that do not match any available function.
- **Custom definition extensibility:** Testing the dynamic regex generator with new function definitions to confirm it can enforce complex schemas without requiring code modifications.

## Resources

#### AI usage

Used for code refactoring, documenting classes according to Google-style standards, and assisting in generating the README.

#### Documentation & research:

##### JSON

[Web: Introducing JSON](https://www.json.org/json-en.html)

##### Constrained decoding

[Web: Non-Invasive Constrained Generation](https://arxiv.org/html/2403.06988v1)\
[Web: Diffusion LLMs can think EoS-by-EoS](https://arxiv.org/html/2603.05197v1)\
[Web: Implementing Constrained Decoding](https://medium.com/@albersj66/part-6-implementing-constrained-decoding-for-phi-3-vision-2c72a1be6a17)
