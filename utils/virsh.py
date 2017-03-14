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
    'freecell': [
        ('all', 'cellno'),
    ],
    'freepages': [
        ('all', 'cellno'),
    ],
    'iothreadinfo': [
        ('current', 'config'),
        ('current', 'live'),
    ],
    'iothreadpin': [
        ('current', 'config'),
        ('current', 'live'),
    ],
    'list': [
        ('table', 'name'),
        ('table', 'uuid'),
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
    'net-list': [
        ('name', 'table'),
        ('name', 'uuid'),
        ('uuid', 'table'),
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

DOMAIN_RUNNING = [
    'shutoff', 'suspend', 'set-user-password', 'domtime'
]

DOMAIN_PAUSED = [
    'resume',
]

DOMAIN_SHUTOFF = [
    'start', 'domrename', 'setmaxmem', 'setmem', 'setvcpus'
]

DOMAIN_RoP = [
    'destroy', 'cpu-stats', 'domdisplay' 'domjobinfo', 'send-key',
    'qemu-monitor-command', 'qemu-monitor-event', 'qemu-agent-command',
    'reboot', 'reset', 'save', 'screenshot', 'vncdisplay', 'domblkerror',
    'domblkstat', 'domcontrol', 'dommemstat',
]

POOL_INA = [
    'pool-delete', 'pool-build', 'pool-undefine'
]


def option_from_line(line):
    option = {'required': False, 'argv': False}
    name, type_name, _ = [i.strip() for i in line.split(' ', 2)]

    if name.startswith('[') and name.endswith(']'):
        name = name[1:-1]
        option['required'] = True

    if name.startswith('<') and name.endswith('>'):
        name = name[1:-1]
        type_name = '<string>'
        option['argv'] = True

    if name.startswith('--'):
        name = name[2:]

    f = open("/home/junli/test2", "a")
    fp = open("/home/junli/test3", "a")
    print >> f, line
    if type_name == '<string>':
        if re.search('domain name', line) or re.search('list of domain', line):
            print >> f, "domain_name"
            type_name = 'string_domname'
        elif re.search('domain', line) and re.search('uuid', line):
            print >> f, "domain_uuid"
            type_name = 'string_nstring'
        elif re.search('pool name', line):
            print >> f, "pool_name"
            type_name = 'string_nstring'
        elif re.search('volume name', line) or re.search('vol name', line):
            print >> f, "volume_name"
            type_name = 'string_nstring'
        elif re.search('network', line) and re.search('name', line):
            print >> f, 'network_name'
            type_name = 'string_nstring'
        elif re.search('network', line) and re.search('uuid', line):
            print >> f, 'network_uuid'
            type_name = 'string_nstring'
        elif re.search('save', line):
            print >> f, ".save"
            type_name = 'string_nstring'
        elif re.search('xml', line) or re.search('XML', line):
            print >> f, "XML"
            type_name = 'string_nstring'
        elif re.search('command', line):
            print >> f, "command"
            type_name = 'string_nstring'
        elif re.search('interface', line):
            print >> f, "interface"
            type_name = 'string_nstring'
        elif re.search('virttype', line):
            print >> f, "virttype"
            type_name = 'string_nstring'
        elif re.search('machine type', line):
            print >> f, "machinetype"
            type_name = 'string_nstring'
        elif re.search('arch', line):
            print >> f, "arch"
            type_name = 'string_nstring'
        elif re.search('emulator', line):
            print >> f, 'emulator'
            type_name = 'string_nstring'
        elif re.search('new name', line) or re.search('clone name', line):
            print >> f, 'name'
            type_name = 'string_nstring'
        elif re.search('secret UUID', line):
            print >> f, 'sec_uuid'
            type_name = 'string_nstring'
        elif re.search('MAC', line):
            print >> f, 'mac'
            type_name = 'string_nstring'
        else:
            type_name = 'string_nstring'
            print >> fp, line
    elif type_name == '<number>':
        type_name = 'number_nnumber'
    else:
        type_name = 'bool'
    option['type'] = type_name
    f.close()
    fp.close()

    return name, option


def command_from_help(name):
    def _parse_options(opt_lines, synopsis):
        options = {}
        last_name = ''
        for line in opt_lines:
            opt_name, opt = option_from_line(line)
            if re.match('string', opt['type']) and opt['required']:
                if ('[<--%s>]' % opt_name in synopsis) or \
                        ('[[--%s] <string>]' % opt_name in synopsis) or \
                        ('[[--%s] <number>]' % opt_name in synopsis):
                    opt['required'] = False
            if re.search('domname', opt['type']):
                f = open('/home/junli/haha', 'a')
                print >>f, name
                f.close()
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


def required_options(command):
    cmd = load_commands()[command]
    req_options = []
    for opt in cmd['options'].keys():
        if cmd['options'][opt]['required'] is True:
            req_options.append(opt)
    return req_options


#  args generate

def string_nstring():
    nstringlist = [u'RHEL-7.2a.xml', u'RHEL-7.2b.xml', u'RHEL-7.2c.xml']
    return list(nstringlist)


def liststring_nstring():
    lstringlist = [u'58', u'rhel58', u'rhel59']
    return list(lstringlist)


def number_nnumber():
    nnumberlist = [2, 4]
    return list(nnumberlist)


def string_domname(state=None):
    if state is None:
        alldom = subprocess.check_output(
            ['virsh', 'list', '--all', '--name']).splitlines()
    elif state == 'running':
        alldom = subprocess.check_output(
            ['virsh', 'list', '--state-running', '--name']).splitlines()
    elif state == 'paused':
        alldom = subprocess.check_output(
            ['virsh', 'list', '--state-paused', '--name']).splitlines()
    elif state == 'shutoff':
        alldom = subprocess.check_output(
            ['virsh', 'list', '--state-shutoff', '--name']).splitlines()
    elif state == 'rop':
        alldom = subprocess.check_output(
            ['virsh', 'list', '--state-running', '--state-paused',
             '--name']).splitlines()

    domlist = [u'RHEL-7.2a.xml', u'RHEL-7.2b.xml', u'RHEL-7.2c.xml']
    for line in alldom:
        dmn = line.strip()
        dmn.decode('utf-8')
        if dmn:
            domlist.append(dmn)
    return domlist


def string_domname_running():
    return string_domname('running')


def string_domname_paused():
    return string_domname('paused')


def string_domname_shutoff():
    return string_domname('shutoff')


def string_domname_rop():
    return string_domname('rop')


def liststring_domname():
    return string_domname()


def string_poolname(ina=False):
    if ina:
        allactpool = subprocess.check_output(
            ['virsh', 'pool-list', '--inactive']).splitlines()
    else:
        allactpool = subprocess.check_output(
            ['virsh', 'pool-list']).splitlines()
    del allactpool[1]
    del allactpool[0]

    poollist = []
    for line in allactpool:
        pool = line.strip()
        pool.decode('utf-8')
        if pool:
            i, _ = re.search(' +', pool).span()
            pool = pool[:i]
            poollist.append(pool)
    return poollist


def string_poolname_ina():
    return string_poolname(True)


def string_volname(pool=None):
    poollist = []
    vollist = []
    if pool:
        poollist.append(pool)
    else:
        poollist = string_poolname()

    for pl in poollist:
        allvol = subprocess.check_output(
            ['virsh', 'vol-list', '--pool', pl]).splitlines()
        del allvol[2]
        del allvol[1]
        del allvol[0]
        for line in allvol:
            vol = line.strip()
            vol.decode('utf-8')
            if vol:
                _, i = re.search(' +', vol).span()
                vol = vol[i:]
                vollist.append(vol)
    return vollist


def stringtype(cmd, command, option):
    otype = cmd['options'][option]['type']
    if re.search('domname', otype):
        if command in DOMAIN_RUNNING:
            otype += '_running'
        elif command in DOMAIN_PAUSED:
            otype += '_paused'
        elif command in DOMAIN_SHUTOFF:
            otype += '_shutoff'
        elif command in DOMAIN_RoP:
            otype += '_rop'
    elif re.search('volname', otype):
        pass
    elif re.search('poolname', otype):
        if command in POOL_INA:
            otype += '_ina'
    elif re.search('network', otype):
        pass
    return otype


def numbertype(cmd, command, option):
    otype = cmd['options'][option]['type']
    return otype


def argtype(command, option):
    cmd = load_commands()[command]
    if (re.match('string', cmd['options'][option]['type']) and
       cmd['options'][option]['argv'] is True):
        return cmd['options'][option]['type'].replace('string', 'liststring', 1)
    elif re.match('bool', cmd['options'][option]['type']):
        return cmd['options'][option]['type']
    elif re.match('string', cmd['options'][option]['type']):
        return stringtype(cmd, command, option)
    elif re.match('number', cmd['options'][option]['type']):
        return numbertype(cmd, command, option)
    else:
        raise Exception('Unexpected cmd:' + command +
                        ' Unexpected option:' + option)
