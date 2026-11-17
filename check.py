"""Optional local test evidence. Duration is suite runtime, not solving time."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
import unittest


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.method_states = []
        self.active = {}
        self.fixture_error_records = 0
        self.error_types = {}

    def startTest(self, test):
        self.active[id(test)] = len(self.method_states)
        self.method_states.append(set())
        super().startTest(test)

    def stopTest(self, test):
        self.active.pop(id(test), None)
        super().stopTest(test)

    def mark(self, test, state):
        parent = getattr(test, 'test_case', test)
        index = self.active.get(id(parent))
        if index is not None:
            self.method_states[index].add(state)
        elif state == 'error':
            self.fixture_error_records += 1

    def addFailure(self, test, err):
        self.mark(test, 'failed_without_error')
        super().addFailure(test, err)

    def addError(self, test, err):
        self.mark(test, 'error')
        self.error_types[test.id()] = err[0].__name__
        super().addError(test, err)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            state = 'failed_without_error' if issubclass(err[0], test.failureException) else 'error'
            self.mark(test, state)
            if state == 'error':
                self.error_types[subtest.id()] = err[0].__name__
        super().addSubTest(test, subtest, err)

    def addSkip(self, test, reason):
        self.mark(test, 'skipped')
        super().addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        self.mark(test, 'expected_failure')
        super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test):
        self.mark(test, 'unexpected_success')
        super().addUnexpectedSuccess(test)

    def outcomes(self):
        priority = ('error', 'failed_without_error', 'unexpected_success', 'expected_failure', 'skipped')
        counts = dict.fromkeys(('passed', *priority), 0)
        for states in self.method_states:
            outcome = next((name for name in priority if name in states), 'passed')
            counts[outcome] += 1
        return counts


def fingerprints(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()
            and '__pycache__' not in p.parts and p.suffix in ('.py', '.md')}


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', choices=('task1', 'task2'))
    parser.add_argument('--record', type=Path, help='new JSON file; existing paths are refused')
    args = parser.parse_args()
    output = args.record.resolve() if args.record else None
    if output and output.exists():
        parser.error(f'record already exists: {output}; choose another path')
    task = Path(__file__).resolve().parent / args.task
    before = fingerprints(task)
    started = datetime.now(timezone.utc).isoformat()
    timer = time.monotonic()
    os.chdir(task)
    sys.path.insert(0, str(task))
    suite = unittest.defaultTestLoader.discover(str(task / 'tests'))
    result = unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult).run(suite)
    duration = time.monotonic() - timer
    record = {
        'schema_version': 1, 'task': args.task, 'started_at_utc': started,
        'suite_seconds': duration, 'duration_scope': 'test execution only',
        'python': sys.version, 'platform': platform.platform(),
        'test_methods_run': result.testsRun,
        'method_outcomes': result.outcomes(),
        'fixture_error_records': result.fixture_error_records,
        'skipped_records': len(result.skipped),
        'failure_records': len(result.failures), 'error_records': len(result.errors),
        'failures': [{'id': t.id(), 'traceback': trace} for t, trace in result.failures],
        'errors': [{'id': t.id(), 'type': result.error_types.get(t.id()), 'traceback': trace}
                   for t, trace in result.errors],
        'task_sha256_before': before, 'task_sha256_after': fingerprints(task),
        'exit_code': 0 if result.wasSuccessful() and result.testsRun else 1,
        'limits': ['No solve time, human effort, cost, or model identity inferred.',
                   'Files and this runner are locally editable; this is evidence, not an anti-cheat oracle.'],
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x') as stream:
            json.dump(record, stream, indent=2)
            stream.write('\n')
        print(f'Check evidence saved to {output}', file=sys.stderr)
    return record['exit_code']


if __name__ == '__main__':
    sys.exit(main())
