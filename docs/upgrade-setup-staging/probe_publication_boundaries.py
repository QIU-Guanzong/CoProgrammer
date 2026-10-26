"""Offline characterization, not a protection guarantee or a model invocation.

Run from a source checkout with PYTHONPATH=src. Each case uses a disposable
synthetic directory. The optimistic variant exists only in memory. JSON reports
observations so a later design can improve them without treating loss as a contract.
"""
import json
import os
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

from coprogrammer import integrations, manager_store, setup


def preregistration_probe():
    source = Path(setup.__file__).read_text()
    publish = '        _replace_event_log(temporary, target)\n'
    record = '            completed.append((relative, content, expected, mode, identity))\n'
    assert source.count(publish) == source.count(record) == 1
    variant = source.replace(publish, '', 1).replace(record, record + publish, 1)
    optimistic = types.ModuleType('coprogrammer._optimistic_probe')
    optimistic.__package__ = 'coprogrammer'
    exec(compile(variant, '<synthetic pre-registration variant>', 'exec'), optimistic.__dict__)
    results = []
    for label, implementation in [('current', setup), ('optimistic_pre_registration', optimistic)]:
        with tempfile.TemporaryDirectory(prefix='setup-boundary-') as directory:
            root = Path(directory).resolve()
            implementation.apply(root, 'claude', edition='mcp')
            target = root / '.mcp.json'
            original = manager_store._replace_event_log
            attempted = False
            foreign = []
            def competitor(source, destination):
                nonlocal attempted
                if destination == target and not attempted:
                    attempted = True
                    alias = root / 'competing-name'
                    os.link(source, alias)
                    os.replace(alias, target)
                    Path(source).unlink()
                    foreign.append((target.read_bytes(), setup._identity(target)))
                    raise KeyboardInterrupt('publication has no confirmed success')
                return original(source, destination)
            with patch.object(integrations.sys, 'executable', integrations.sys.executable + '-synthetic-moved'):
                with patch.object(manager_store, '_replace_event_log', competitor):
                    try:
                        implementation.apply(root, 'claude', edition='mcp', upgrade=True)
                    except KeyboardInterrupt:
                        pass
                    else:
                        raise AssertionError('probe did not reach interruption')
            results.append({'case': 'same-inode foreign publication without confirmation',
                            'implementation': label,
                            'foreign_name_preserved': (target.read_bytes(), setup._identity(target)) == foreign[0]})
    return results


def post_check_probe():
    with tempfile.TemporaryDirectory(prefix='setup-boundary-') as directory:
        root = Path(directory).resolve()
        setup.apply(root, 'claude', edition='mcp')
        target = root / '.mcp.json'
        helper, primitive = setup._replace, manager_store._replace_event_log
        recovering = False
        foreign = []
        def fail_receipt(project, relative, *args):
            nonlocal recovering
            if relative == setup.MANIFEST_PATH:
                recovering = True
                raise KeyboardInterrupt('synthetic receipt interruption')
            return helper(project, relative, *args)
        def late_write(source, destination):
            if recovering and destination == target:
                replacement = root / 'late-foreign'
                replacement.write_bytes(b'synthetic foreign edit after final check')
                os.replace(replacement, target)
                foreign.append((target.read_bytes(), setup._identity(target)))
            return primitive(source, destination)
        with patch.object(integrations.sys, 'executable', integrations.sys.executable + '-synthetic-moved'):
            with patch.object(setup, '_replace', fail_receipt), patch.object(manager_store, '_replace_event_log', late_write):
                try:
                    setup.apply(root, 'claude', edition='mcp', upgrade=True)
                except KeyboardInterrupt:
                    pass
                else:
                    raise AssertionError('probe did not reach recovery')
        assert len(foreign) == 1
        return {'case': 'external replacement after final rollback check',
                'foreign_name_preserved': (target.read_bytes(), setup._identity(target)) == foreign[0],
                'classification': 'not an atomic filesystem compare-and-swap'}


if __name__ == '__main__':
    print(json.dumps({'observations': preregistration_probe() + [post_check_probe()],
                      'production_source_modified': False,
                      'model_calls': 0,
                      'fixtures_removed': True}, indent=2))
