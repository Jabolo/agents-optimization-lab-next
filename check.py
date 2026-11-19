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

SUPPLIED_TEST_MODULES = {
    'task1': frozenset({'test_stock'}),
    'task2': frozenset({'test_reservations', 'test_amendments', 'test_recovery', 'test_rebuild'}),
}

STARTER_TEST_SHA256 = {
    'task1': {
        'tests/test_stock.py': 'fb1a447a9d12f97fb25c0b6af3a98b841fb04449329fd5f0b83b3f8d9f25569b',
    },
    'task2': {
        'tests/test_amendments.py': '547e4e684ecd7e3a7113f295606d9b9260573f4c8507f8ac6af0f6148ac6fae7',
        'tests/test_rebuild.py': 'a7b2a2dc52cab8679e7110e97481e056d512703524faa95812fc2c5e92364d76',
        'tests/test_recovery.py': '6e1d9c1250c75efc1f8776b2f09be336b2ca8a884f7a010c5ceb3f1a68dc712a',
        'tests/test_reservations.py': '1f8a40366ba30ab1d69a2612e5861c06f28196c5fb8c87484fb2c94c9885232f',
    },
}


def _test_module_name(test_id):
    if test_id.startswith('unittest.loader._FailedTest.'):
        return test_id.removeprefix('unittest.loader._FailedTest.')
    return test_id.split('.', 1)[0]


def _extract_fixture_target(test_id):
    if '(' in test_id and test_id.endswith(')'):
        return test_id.split('(', 1)[1][:-1]
    return ''


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.method_states = []
        self.method_ids = []
        self.active = {}
        self.class_methods = {}
        self.fixture_error_records = 0
        self.setup_import_errors = 0
        self.error_types = {}

    @staticmethod
    def _is_failed_test(test):
        return test.__class__.__name__ == '_FailedTest' or test.id().startswith('unittest.loader._FailedTest.')

    def startTest(self, test):
        index = len(self.method_states)
        test_id = test.id()
        self.active[id(test)] = index
        self.method_states.append(set())
        self.method_ids.append(test_id)
        class_key = test_id.rsplit('.', 1)[0] if '.' in test_id else test_id
        self.class_methods.setdefault(class_key, []).append(index)
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
            test_id = test.id()
            self.fixture_error_records += 1
            if 'tearDownClass' in test_id:
                class_key = _extract_fixture_target(test_id)
                for method_index in self.class_methods.get(class_key, ()):
                    self.method_states[method_index].add('error')
            elif 'tearDownModule' in test_id:
                module_key = _extract_fixture_target(test_id)
                for class_key, indices in self.class_methods.items():
                    if class_key == module_key or class_key.startswith(f'{module_key}.'):
                        for method_index in indices:
                            self.method_states[method_index].add('error')

    def addFailure(self, test, err):
        self.mark(test, 'failed_without_error')
        super().addFailure(test, err)

    def addError(self, test, err):
        if self._is_failed_test(test):
            self.setup_import_errors += 1
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

    def outcomes(self, predicate=None):
        priority = ('error', 'failed_without_error', 'unexpected_success', 'expected_failure', 'skipped')
        counts = dict.fromkeys(('passed', *priority), 0)
        for test_id, states in zip(self.method_ids, self.method_states):
            if predicate is not None and not predicate(test_id):
                continue
            outcome = next((name for name in priority if name in states), 'passed')
            counts[outcome] += 1
        return counts


def fingerprints(root):
    result = {}
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if '__pycache__' in rel.parts or p.suffix == '.pyc' or p.name == '.DS_Store':
            continue
        result[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def find_unexecuted_test_subdirs(task):
    tests_dir = task / 'tests'
    if not tests_dir.is_dir():
        return []
    found = []
    for path in sorted(tests_dir.rglob('*')):
        if not path.is_dir():
            continue
        rel_tests = path.relative_to(tests_dir)
        if '__pycache__' in rel_tests.parts:
            continue
        if not any(item.is_file() and item.suffix == '.py' for item in path.iterdir()):
            continue
        # Discover skips a subdir whenever it or an ancestor under tests/ lacks __init__.py.
        current = path
        missing_init = False
        while current != tests_dir:
            if not (current / '__init__.py').is_file():
                missing_init = True
                break
            current = current.parent
        if missing_init:
            found.append(path.relative_to(task).as_posix())
    return found


def safe_stderr(line):
    try:
        print(line, file=sys.stderr)
    except UnicodeEncodeError:
        enc = getattr(sys.stderr, 'encoding', None) or 'ascii'
        print(line.encode(enc, errors='replace').decode(enc), file=sys.stderr)


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', choices=('task1', 'task2'))
    parser.add_argument('-p', '--pattern', default='test*.py', help='test file pattern passed to unittest discover')
    parser.add_argument('-k', '--filter', action='append', help='test name pattern passed to unittest discover')
    parser.add_argument('--record', type=Path, help='new JSON file; existing paths are refused')
    args = parser.parse_args()
    output = None
    if args.record:
        raw_output = Path(os.path.abspath(args.record))
        if raw_output.exists() or raw_output.is_symlink():
            parser.error(f'record already exists: {raw_output}; choose another path')
        output = raw_output.resolve()
    runner_sha256 = hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()
    task = Path(__file__).resolve().parent / args.task
    before = fingerprints(task)
    expected_tests = STARTER_TEST_SHA256[args.task]
    changed_tests = sorted(path for path, digest in expected_tests.items() if before.get(path) != digest)
    supplied_intact = not changed_tests
    unexecuted_subdirs = find_unexecuted_test_subdirs(task)
    filtered = bool(args.pattern != 'test*.py' or args.filter)
    started = datetime.now(timezone.utc).isoformat()
    timer = time.monotonic()
    os.chdir(task)
    sys.path.insert(0, str(task))
    loader = unittest.TestLoader()
    if args.filter:
        loader.testNamePatterns = [f'*{p}*' if '*' not in p else p for p in args.filter]
    suite = loader.discover(str(task / 'tests'), pattern=args.pattern)
    result = unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult).run(suite)
    duration = time.monotonic() - timer
    outcomes = result.outcomes()
    supplied_modules = SUPPLIED_TEST_MODULES[args.task]
    supplied_outcomes = result.outcomes(lambda test_id: _test_module_name(test_id) in supplied_modules)
    added_outcomes = result.outcomes(lambda test_id: _test_module_name(test_id) not in supplied_modules)
    exit_code = 0 if (
        result.wasSuccessful()
        and result.testsRun > 0
        and outcomes['passed'] > 0
        and result.fixture_error_records == 0
        and result.setup_import_errors == 0
    ) else 1
    record = {
        'schema_version': 1, 'task': args.task, 'started_at_utc': started,
        'suite_seconds': duration, 'duration_scope': 'test execution only',
        'python': sys.version, 'platform': platform.platform(),
        'runner_sha256': runner_sha256,
        'filters': {'pattern': args.pattern, 'name_patterns': args.filter or []},
        'filtered': filtered,
        'test_methods_run': result.testsRun,
        'method_outcomes': outcomes,
        'supplied_method_outcomes': supplied_outcomes,
        'added_method_outcomes': added_outcomes,
        'supplied_tests_intact': supplied_intact,
        'supplied_tests_changed': changed_tests,
        'unexecuted_test_subdirs': unexecuted_subdirs,
        'fixture_error_records': result.fixture_error_records,
        'setup_import_errors': result.setup_import_errors,
        'skipped_records': len(result.skipped),
        'failure_records': len(result.failures), 'error_records': len(result.errors),
        'failures': [{'id': t.id(), 'traceback': trace} for t, trace in result.failures],
        'errors': [{'id': t.id(), 'type': result.error_types.get(t.id()), 'traceback': trace}
                   for t, trace in result.errors],
        'task_sha256_before': before, 'task_sha256_after': fingerprints(task),
        'exit_code': exit_code,
        'limits': ['No solve time, human effort, cost, or model identity inferred.',
                   'Files and this runner are locally editable; this is evidence, not an anti-cheat oracle.'],
    }
    summary = (
        f"Summary ({args.task}, test execution only \u2014 NOT solve time): "
        f"methods={result.testsRun} passed={outcomes['passed']} "
        f"failed={outcomes['failed_without_error']} error={outcomes['error']} "
        f"skipped={outcomes['skipped']} fixture_errors={result.fixture_error_records} "
        f"setup_errors={result.setup_import_errors} | "
        f"supplied_tests_intact={supplied_intact} | "
        f"supplied={sum(supplied_outcomes.values())} added={sum(added_outcomes.values())}"
    )
    if filtered:
        summary += ' | FILTERED (-p/-k)'
    safe_stderr(summary)
    if not supplied_intact:
        safe_stderr(f"WARNING: supplied tests differ from starter baseline: {', '.join(changed_tests)}")
    if unexecuted_subdirs:
        safe_stderr(f"WARNING: unexecuted test subdirectories without __init__.py: {', '.join(unexecuted_subdirs)}")
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as stream:
            json.dump(record, stream, indent=2)
            stream.write('\n')
        print(f'Check evidence saved to {output}', file=sys.stderr)
    return record['exit_code']


if __name__ == '__main__':
    sys.exit(main())
