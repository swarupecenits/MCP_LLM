#!/bin/bash

TEST_DIR="apps/ai-studio/tests-e2e-playwright"
RESULTS_DIR="playwright-results"
HEALED_DIR="healed_tests"
SELF_HEAL_SCRIPT="scripts/e2e-test-generator/self_heal.py"

mkdir -p "$RESULTS_DIR"
mkdir -p "$HEALED_DIR"

# Find the first .spec.ts file
testfile=$(find "$TEST_DIR" -type f -name "*.spec.ts" | head -n 1)
if [ -z "$testfile" ]; then
  echo "No .spec.ts files found in $TEST_DIR"
  exit 1
fi

testname=$(basename "$testfile" .spec.ts)
resultfile="$RESULTS_DIR/${testname}-result.json"
errorlog="$RESULTS_DIR/${testname}-error.log"

# Change to the Playwright config directory
cd apps/ai-studio || exit 1

# Make testfile path relative to current directory
relative_testfile=$(realpath --relative-to=. "../$testfile")

echo "Running Playwright test: $relative_testfile"
# Run Playwright with JSON reporter, redirect JSON to resultfile, and errors/warnings to errorlog
npx --loglevel=error playwright test "$relative_testfile" --reporter=json --trace on > "../$resultfile" 2> "../$errorlog"
exit_code=$?

echo "Test result saved to ../$resultfile"
echo "Errors/warnings logged to ../$errorlog"

# Check if resultfile contains valid JSON
if ! jq . "../$resultfile" >/dev/null 2>&1; then
  echo "Error: ../$resultfile is not valid JSON. Contents:"
  cat "../$resultfile"
  echo "Error log contents:"
  cat "../$errorlog"
  exit 1
fi

if [ $exit_code -ne 0 ]; then
  echo "Test failed, running trace and producing result.json"
else
  echo "Test passed, skipping self-healing."
  exit 0
fi

echo "Running self-healing script for ../$testfile"
python "../$SELF_HEAL_SCRIPT" --script "../$testfile" --error "../$resultfile"
echo "Self-healing complete for ../$testfile"