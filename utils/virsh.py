import json
import logging
import os
import re
import subprocess

from dice.utils import data_dir


EXCLUSIVE_OPTIONS = {
    'allocpages': [
        ('all', 'cellno'),
    ],
    'attach-device': [
        ('persistent', 'current'),
        ('current', 'config'),
        ('current', 'live'),
    ],
    'attach-disk': [
        ('persistent', 'current'),
        ('current', 'config'),
        ('current', 'live'),
    ],
    'attach-interface': [
        ('persistent', 'current'),
        ('current', 'config'),
        ('current', 'live'),
    ],
    'blockcopy': [
        ('blockdev', 'xml'),
        ('dest', 'xml'),
        ('format', 'xml'),
    ],
    'blockjob': [
        ('abort', 'info'),
        ('async', 'info'),
        ('pivot', 'info'),
        ('abort', 'raw'),
        ('async', 'raw'),
        ('pivot', 'raw'),
        ('abort', 'bandwidth'),
        ('async', 'bandwidth'),
        ('pivot', 'bandwidth'),
        ('info', 'bandwidth'),
        ('raw', 'bandwidth'),
    ],
    'blkdeviotune': [
        ('current', 'config'),
        ('current', 'live'),
        ('total-iops-sec', 'write-iops-sec'),
        ('total-iops-sec', 'read-iops-sec'),
        ('total-iops-sec-max', 'write-iops-sec-max'),
        ('total-iops-sec-max', 'read-iops-sec-max'),
        ('total-bytes-sec', 'write-bytes-sec'),
        ('total-bytes-sec', 'read-bytes-sec'),
        ('total-bytes-sec-max', 'write-bytes-sec-max'),
        ('total-bytes-sec-max', 'read-bytes-sec-max'),
    ],
    'blkiotune': [
        ('current', 'config'),
        ('current', 'live'),
    ],
    'change-media': [
        ('eject', 'block'),
        ('eject', 'insert'),
        ('eject', 'update'),
        ('insert', 'update'),
        ('current', 'config'),
        ('current', 'live'),
    ],
    'desc': [
        ('current', 'live'),
        ('current', 'config'),
    ],
    'detach-device': [
        ('persistent', 'current'),
        ('current', 'config'),
        ('current', 'live'),
    ],
    'detach-disk': [
        ('persistent', 'current'),
        ('current', 'live'),
        ('current', 'config'),
    ],
    'detach-interface': [
        ('persistent', 'current'),
        ('current', 'config'),
        ('current', 'live'),
    ],
    'domiftune': [
        ('current', 'config'),
        ('current', 'live'),
    ],
    'dommemstat': [
        ('current', 'config'),
        ('current', 'live'),
    ],
    'domtime': [
        ('now', 'sync'),
        ('time', 'now'),
        ('time', 'sync'),
    ],
    'emulatorpin': [
        ('current', 'config'),
        ('current', 'live'),
    ],
    'iothreadinfo': [
        ('current', 'config'),
        ('current', 'live'),
    ],
    'iothreadpin': [
        ('current', 'config'),
        ('current', 'live'),
    ],
    'freecell': [
        ('all', 'cellno'),
    ],
    'freepages': [
        ('all', 'cellno'),
    ],
    'metadata': [
        ('edit', 'set'),
        ('current', 'config'),
        ('current', 'live'),
        ('remove', 'edit'),
        ('remove', 'set'),
    ],
    'memtune': [
        ('current', 'config'),
        ('current', 'live'),
    ],
    'numatune': [
        ('current', 'config'),
        ('current', 'live'),
    ],
    'restore': [
        ('running', 'paused'),
    ],
    'save-image-edit': [
        ('running', 'paused'),
    ],
    'setvcpus': [
        ('guest', 'config'),
        ('current', 'live'),
        ('current', 'config'),
    ],
    'setmaxmem': [
        ('current', 'live'),
        ('current', 'config'),
    ],
    'setmem': [
        ('current', 'live'),
        ('current', 'config'),
    ],
    'schedinfo': [
        ('current', 'live'),
        ('current', 'config'),
    ],
    'snapshot-current': [
        ('name', 'snapshotname'),
    ],
    'snapshot-edit': [
        ('rename', 'clone'),
    ],
    'snapshot-list': [
        ('active', 'tree'),
        ('current', 'tree'),
        ('disk-only', 'tree'),
        ('external', 'tree'),
        ('inactive', 'tree'),
        ('internal', 'tree'),
        ('leaves', 'tree'),
        ('no-leaves', 'tree'),
        ('roots', 'from'),
        ('roots', 'tree'),
        ('roots', 'current'),
        ('tree', 'name'),
        ('parent', 'tree'),
        ('parent', 'roots'),
    ],
    'update-device': [
        ('persistent', 'current'),
        ('current', 'config'),
        ('current', 'live'),
    ],
    'vcpucount': [
        ('active', 'maximum'),
        ('guest', 'config'),
        ('live', 'config'),
        ('current', 'config'),
        ('current', 'live'),
    ],
    'vcpupin': [
        ('current', 'config'),
        ('current', 'live'),
        ('live', 'config'),
    ],
}


def option_from_line(line):
    option = {'required': False, 'argv': False}
    name, type_name, _ = [i.strip() for i in line.split(' ', 2)]

    if name.startswith('[') and name.endswith(']'):
        name = name[1:-1]
        option['required'] = True

    if name.startswith('<') and name.endswith('>'):
        if name == '<string>':
            # Special case for 'virsh echo'
            name = ''
            type_name = '<string>'
        else:
            name = name[1:-1]

    if name.startswith('--'):
        name = name[2:]

    if type_name == '<string>':
        type_name = 'string'
    elif type_name == '<number>':
        type_name = 'number'
    else:
        type_name = 'bool'
    option['type'] = type_name

    return name, option


def command_from_help(name):
    def _parse_options(opt_lines, synopsis):
        options = {}
        last_name = ''
        for line in opt_lines:
            opt_name, opt = option_from_line(line)
            if opt['type'] == 'string' and opt['required']:
                if '[<%s>]' % opt_name in synopsis:
                    opt['required'] = False
            options[opt_name] = opt
            last_name = opt_name

        if '...' in synopsis:
            options[last_name]['argv'] = True
        return options

    help_contents = {}
    help_txt = subprocess.check_output(
        ['virsh', 'help', name]).splitlines()

    item_name = ''
    item_content = []
    for line in help_txt:
        if re.match(r'^  [A-Z]*$', line):
            if item_name:
                if item_name == 'options':
                    help_contents[item_name] = item_content
                else:
                    help_contents[item_name] = ''.join(item_content)
                item_content = []
            item_name = line.strip().lower()
        else:
            if line:
                item_content.append(line.strip())
    if item_name:
        if item_name == 'options':
            help_contents[item_name] = item_content
        else:
            help_contents[item_name] = ''.join(item_content)
        item_content = []

    cmd = {'options': {}, 'exclusives': {}}
    if 'options' in help_contents:
        cmd['options'] = _parse_options(
            help_contents['options'],
            help_contents['synopsis'])

    if name in EXCLUSIVE_OPTIONS:
        cmd['exclusives'] = EXCLUSIVE_OPTIONS[name]
    return cmd


def cmd_names_from_help():
    names = []
    for line in subprocess.check_output(['virsh', 'help']).splitlines():
        if line.startswith('    '):
            name = line.split()[0]
            names.append(name)
    return names


def load_cmds_from_path(path):
    with open(path, 'r') as fp:
        cmds = json.load(fp)
        return cmds


def load_cmds_from_help(path=None):
    cmds = {}
    for cmd_name in cmd_names_from_help():
        cmds[cmd_name] = command_from_help(cmd_name)
    if path:
        try:
            with open(path, 'w') as fp:
                json.dump(cmds, fp)
        except IOError:
            logging.error('Failed to save virsh commands info to %s', path)
    return cmds


def load_commands():
    path = os.path.join(data_dir.USER_BASE_DIR, 'virsh')
    try:
        return load_cmds_from_path(path)
    except IOError:
        return load_cmds_from_help(path=path)


def commands(excludes=None):
    excludes = ['qemu-monitor-event']
    cmds = load_commands().keys()
    if excludes is None:
        return cmds
    else:
        return list(set(load_commands().keys()) - set(excludes))


def options(command):
    cmd = load_commands()[command]
    return cmd['options'].keys()


def exclusive_options(command):
    cmd = load_commands()[command]
    return cmd['exclusives']
