_This project was developed as part of the 42 curriculum by nlallema_

# Call me maybe

## Table of Contents

- [Description](#description)
- [Usage](#usage)
- [File Formats](#file-formats)
- [Algorithm](#algorithm)
- [Design Decisions](#design-decisions)
- [Performance Analysis](#performance-analysis)
- [Challenges Faced](#challenges-faced)
- [Testing Strategy](#testing-strategy)
- [Resources](#resources)

## Description

**Call-me-maybe** is a command-line utility designed to translate natural language queries into structured, schema-compliant JSON function calls. Powered by the Qwen3-0.6B model, the project leverages a highly constrained inference architecture. This ensures that the generated output strictly adheres to predefined data schemas, reliably overcoming the typical limitations of small-scale language models.

## Usage

### Installation

Install dependencies and set up the environment via uv:
```bash
make install
```

### Execution

By default, the program processes files in `data/input/` and writes the results to `data/output/`:
```bash
make run [ARGS="..."]
```

> This command automatically triggers `make install` to ensure the environment is fully ready before execution.

#### Arguments & Options

| Argument / Flag | Description |
|-----------------|-------------|
| --functions_definition | path to function definitions (default: data/input/functions_definition.json) (format: json) |
| --input | path to user prompts (default: data/input/function_calling_tests.json) (format: json) |
| --output | output file path for results (default: data/output/function_calls.json) (format: json) |
| -t, --timeout | inference time limit in milliseconds (default: 20000) |
| -v, -vv | log verbosity levels (INFO or DEBUG levels) |
| -S, --stop-on-first-error | halt execution immediately upon the first processing error |
| --help, -h | show the help message and exit |

#### Development Commands

| Command | Description |
|---------|-------------|
| make clean | remove temporary files and project caches |
| make cache-clean | specifically clear local project caches (e.g., mypy, \_\_pycache__) |
| make lint | check code against flake8 and mypy standards |
| make lint-strict | execute strict linting using mypy --strict |
| make debug | run the program using the Python built-in debugger |

## File Formats

The program relies on structured JSON files to configure the model's capabilities and define the tasks to process.

### Function Definitions (`functions_definition.json`)

This file contains a list of objects defining the tools available to the LLM. Each object must follow this strict schema:

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

### Input Prompts (`function_calling_tests.json`)

This file lists the natural language requests that the system must process.

- `prompt` (string): The user query.

**Example:**

```json
[
  { "prompt": "What is the weather in Paris?" },
  { "prompt": "Calculate the sum of 10 and 5." }
]
```

### Output Results (`function_calls.json`)

The generated file contains structured function calls resulting from the inference process. Each entry includes the original prompt along with the extracted data:

- `prompt` (string): The original query.
- `name` (string): The identified function name.
- `parameters` (object): The extracted arguments with correctly coerced types.

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

> **Note:** All files are validated at load time. If a required field is missing or a type is incorrect, the program immediately raises a `SchemaValidationError`.

## Algorithm

The core implementation relies on an inference loop governed by dynamic syntax constraints:

- **Regex Pattern Generation:** A strict regex pattern is dynamically constructed for each target function. It defines the exact expected JSON structure, enforcing parameter types (string, number, boolean).
- **Constrained Inference:** During token-by-token generation, the system decodes candidate tokens and evaluates them against the active regex pattern using partial matching.
- **Logits Filtering:** Only tokens that preserve a valid JSON structure and comply with the function schema are authorized. Any token violating the syntax or type constraints is discarded in favor of the next highest-probability candidate.
- **Fallback Management:** A default `function_not_implemented_yet` tool is systematically injected into the context, empowering the model to gracefully handle queries that fall outside the scope of defined functions.

## Design Decisions

- **Pydantic for Data Integrity:** All internal data structures are strictly typed using Pydantic `BaseModel`. Enforcing `extra="forbid"` and `frozen=True` guarantees absolute schema compliance and eliminates silent data mutation across the pipeline.
- **Three-Stage Inference Pipeline:** To maximize the accuracy of the 0.6B parameter model, the workflow is divided into three focused passes:
  - *Intent Clarification:* The first pass rephrases the user's raw prompt to extract a clean, context-aware description of their core intent.
  - *Function Routing:* The second pass matches this clarified intent against available tool descriptions to accurately identify the target function.
  - *Parameter Extraction:* The final pass is heavily constrained and focuses solely on extracting and typing the specific arguments required by the chosen schema.
- **Constrained Decoding via Regex:** Instead of relying on the model's spontaneous formatting capabilities, the system uses dynamic regex patterns to filter logits. This guarantees that every generated token contributes to a syntactically valid JSON object.
- **Strict Inference Timeout:** A millisecond timer monitors each inference cycle against the user-defined `--timeout` to prevent infinite loops or stalled processing on highly ambiguous prompts.
- **Granular Error Domain Isolation:** The application separates concerns through a custom exception hierarchy:
  - *StorageError:* Handles filesystem issues such as permissions or missing files.
  - *SchemaError:* Manages data integrity issues, including invalid JSON structures, Pydantic validation failures and missing Constraint builder arguments.

## Performance Analysis

- **Deterministic Type Coercion:** The system guarantees typing reliability through a formatting engine that injects specialized regex placeholders directly into the generation sequence:
  - *Numbers:* Constrained to signed integers, decimals, and scientific notation (e.g., `-1.23e+10` or `.2`).
  - *Booleans:* Strictly limited to the `true` or `false` tokens.
  - *Strings:* Confined within literal quote boundaries to prevent JSON escaping errors.
- **Latency vs. Accuracy Trade-off:** Although regex-based constrained decoding introduces a marginal computational overhead during logit filtering, it pays off by guaranteeing 100% syntactically valid JSON outputs and flawless argument typing.
- **Multi-Stage Latency Impact:** While the three-stage inference pipeline is crucial for the 0.6B model's accuracy, it inherently increases total execution time. Performing three distinct LLM calls, combined with the large context windows required by extensive prompts and function descriptions, introduces noticeable latency compared to a standard single-pass approach.

## Challenges Faced

- **Real-Time Token Validation (Partial Inference):** Because LLMs stream text token by token, standard regex matching is inadequate as it requires complete strings. To overcome this, the engine employs `regex.fullmatch` with the `partial=True` flag. This allows the system to determine if an incomplete, mid-generation string can still logically resolve into a valid match, effectively filtering out invalid syntactic branches in real-time.
- **Model Precision & Task Decomposition:** Achieving high accuracy with a compact 0.6B parameter model is notoriously difficult when asking it to perform complex reasoning in a single pass. To compensate for this inherent lack of precision, the architecture had to be split into the three-stage pipeline. By strictly isolating intent clarification, function routing, and parameter extraction, the model's cognitive load is minimized, drastically improving overall reliability.
- **Context Window Limitations & Definition Chunking:** During the second stage (Function Routing), injecting the descriptions of all available functions into a single prompt often overwhelmed the model's limited context window, leading to degraded decision-making or truncated inputs. To solve this, the engine implements a chunking mechanism that batches function definitions into smaller, manageable groups. This ensures the model evaluates each subset of tools effectively without exceeding its context limits.
- **Fallback via Systematic Injection:** To maintain reliability during the chunked routing process, a specialized `function_not_implemented_yet` definition is systematically injected into every single batch. This provides the model with a consistent fallback option, allowing it to explicitly reject a match within a specific subset if no coherent function is found, rather than forcing an incorrect or hallucinated selection.

## Testing Strategy

- **Schema Validation:** Compliance testing of Pydantic models using the `extra="forbid"` option to detect any drift or unexpected fields in input data.
- **I/O Robustness:** Management of file permissions and automatic directory creation to ensure results are saved safely, even if the target path is missing.
- **Prompt Edge Cases:** Systematic validation against a variety of input scenarios to ensure stable behavior:
  - *Empty Prompts:* Ensuring the pipeline identifies and skips empty input strings to prevent wasted inference cycles.
  - *Ambiguous Prompts:* Testing the model's ability to remain within regex constraints even when the natural language intent is unclear.
  - *Unmapped Prompts:* Verifying that the `function_not_implemented_yet` fallback correctly handles requests that do not match any available function.
- **Custom Definition Extensibility:** Testing the dynamic regex generator with new function definitions to confirm it can enforce complex schemas without requiring underlying code modifications.

## Resources

### AI Usage Acknowledgement

The development of this project was supported by AI for:
- **Code Refactoring**
- **Documentation**: Generating Google-style docstrings.
- **Prompt Engineering**: Assisting in the design and generation of some prompts.
- **Project Communication**: Drafting and formatting the README.

### Research & Documentation

#### Python & Tooling

- [Web: Introducing JSON](https://www.json.org/json-en.html)
- [Web: Advanced Regex Implementation](https://pypi.org/project/regex/)
- [Web: Creating Python Context Managers](https://www.pythonmorsels.com/creating-a-context-manager/#:~:text=Context%20managers%20are%20objects%20that,Python%20Tutor%20context%20manager%20example.)

#### Constrained Decoding Techniques

- [Web: Non-Invasive Constrained Generation](https://arxiv.org/html/2403.06988v1) — Research on enforcing syntax without retraining models.
- [Web: Diffusion LLMs can think EoS-by-EoS](https://arxiv.org/html/2603.05197v1) — Insights into token-level control during generation.
- [Web: Implementing Constrained Decoding](https://medium.com/@albersj66/part-6-implementing-constrained-decoding-for-phi-3-vision-2c72a1be6a17) — A guide on logit filtering and schema enforcement.
