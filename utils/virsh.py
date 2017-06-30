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
    'shutoff', 'suspend', 'set-user-password', 'domtime',
]

DOMAIN_PAUSED = [
    'resume',
]

DOMAIN_SHUTOFF = [
    'start', 'domrename', 'setmaxmem', 'setmem', 'setvcpus',
]

DOMAIN_RoP = [
    'destroy', 'cpu-stats', 'domdisplay' 'domjobinfo', 'send-key',
    'qemu-monitor-command', 'qemu-monitor-event', 'qemu-agent-command',
    'reboot', 'reset', 'save', 'screenshot', 'vncdisplay', 'domblkerror',
    'domblkstat', 'domcontrol', 'dommemstat',
]

POOL_INA = [
    'pool-delete', 'pool-build', 'pool-undefine', 'migrate-compcache',
    'migrate-setmaxdowntime',
]


XML_DOMAIN = [
    'define',
]


XML_NET = [

]


XML_POOL = [

]


XML_VOL = [

]


XML_NETFLT = [

]


XML_IF = [

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

    if type_name == '<string>':
        if (re.search('domain name', line)
            or re.search('list of domain', line))\
                and not re.search('new', line):
            type_name = 'string_domname'
        elif re.search('domain', line) and re.search('uuid', line):
            type_name = 'string_nstring'
        elif re.search('pool name', line):
            type_name = 'string_poolname'
        elif re.search('volume name', line) or re.search('vol name', line):
            type_name = 'string_volname'
        elif re.search('network', line) and re.search('name', line):
            type_name = 'string_netname'
        elif re.search('network', line) and re.search('uuid', line):
            type_name = 'string_nstring'
        elif re.search('save', line):
            type_name = 'string_nstring'
        elif re.search('xml', line) or re.search('XML', line):
            type_name = 'string_nstring'
        elif re.search('command', line):
            type_name = 'string_nstring'
        elif re.search('interface', line):
            type_name = 'string_nstring'
        elif re.search('virttype', line):
            type_name = 'string_nstring'
        elif re.search('machine type', line):
            type_name = 'string_nstring'
        elif re.search('arch', line):
            type_name = 'string_nstring'
        elif re.search('emulator', line):
            type_name = 'string_nstring'
        elif re.search('new name', line) or re.search('clone name', line):
            type_name = 'string_nstring'
        elif re.search('secret UUID', line):
            type_name = 'string_nstring'
        elif re.search('MAC', line):
            type_name = 'string_nstring'
        else:
            type_name = 'string_nstring'
    elif type_name == '<number>':
        type_name = 'number_nnumber'
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


def commands(excludes=[]):
    excludes += ['qemu-monitor-event', 'pool-delete']
    cmds = load_commands().keys()
    if len(excludes) == 0:
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


def define_dom():
    xmllist = []
    assert len(xmllist) > 0
    for xml in xmllist:
        subprocess.call(['virsh', 'define', xml])


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

    domlist = []
    for line in alldom:
        dmn = line.strip()
        dmn = dmn.decode('utf-8')
        if dmn:
            domlist.append(dmn)
    if len(domlist) == 0 and state is None:
        define_dom()
        domlist = string_domname()
    return domlist


def destroy_dom():
    domlist = string_domname()
    for dom in domlist:
        subprocess.call(['virsh', 'destroy', str(dom)])


def string_domname_shutoff():
    domlist = string_domname('shutoff')
    if len(domlist) == 0:
        destroy_dom()
        domlist = string_domname_shutoff()
    return domlist


def start_dom():
    domlist = string_domname_shutoff()
    for dom in domlist:
        subprocess.call(['virsh', 'start', str(dom)])


def string_domname_running():
    domlist = string_domname('running')
    if len(domlist) == 0:
        start_dom()
        domlist = string_domname_running()
    return domlist


def suspend_dom():
    domlist = string_domname_running()
    for dom in domlist:
        subprocess.call(['virsh', 'suspend', str(dom)])


def string_domname_paused():
    domlist = string_domname('paused')
    if len(domlist) == 0:
        suspend_dom()
        domlist = string_domname_paused()
    return domlist


def string_domname_rop():
    domlist = string_domname('rop')
    if len(domlist) == 0:
        domlist = string_domname_running()
    return domlist


def liststring_domname():
    return string_domname()


def define_pool():
    xmllist = []
    assert len(xmllist) > 0
    for xml in xmllist:
        subprocess.call(['virsh', 'pool-define', xml])


def string_poolname(state=None):
    if state is None:
        allactpool = subprocess.check_output(
            ['virsh', 'pool-list', '--all']).splitlines()
    elif state == 'ina':
        allactpool = subprocess.check_output(
            ['virsh', 'pool-list', '--inactive']).splitlines()
    elif state == 'act':
        allactpool = subprocess.check_output(
            ['virsh', 'pool-list']).splitlines()
    del allactpool[1]
    del allactpool[0]

    poollist = []
    for line in allactpool:
        pool = line.strip()
        pool = pool.decode('utf-8')
        if pool:
            i, _ = re.search(' +', pool).span()
            pool = pool[:i]
            poollist.append(pool)

    if len(poollist) == 0 and state is None:
        define_pool()
        poollist = string_poolname()

    return poollist


def ina_pool():
    poollist = string_poolname()
    for pool in poollist:
        subprocess.call(['virsh', 'pool-destroy', str(pool)])
    return poollist


def string_poolname_ina():
    poollist = string_poolname('ina')
    if len(poollist) == 0:
        poollist = ina_pool()
    return poollist


def act_pool():
    poollist = string_poolname_ina()
    for pool in poollist:
        subprocess.call(['virsh', 'pool-start', str(pool)])
    return poollist


def string_poolname_act():
    poollist = string_poolname('act')
    if len(poollist) == 0:
        poollist = act_pool()
    return poollist


def define_net():
    xmllist = []
    assert len(xmllist) > 0
    for xml in xmllist:
        subprocess.call(['virsh', 'net-define', xml])


def string_netname(state=None):
    if state is None:
        allactnet = subprocess.check_output(
            ['virsh', 'net-list', '--all']).splitlines()
    elif state == 'ina':
        allactnet = subprocess.check_output(
            ['virsh', 'net-list', '--inactive']).splitlines()
    elif state == 'act':
        allactnet = subprocess.check_output(
            ['virsh', 'net-list']).splitlines()
    del allactnet[1]
    del allactnet[0]

    netlist = []
    for line in allactnet:
        net = line.strip()
        net = net.decode('utf-8')
        if net:
            i, _ = re.search(' +', net).span()
            net = net[:i]
            netlist.append(net)

    if len(netlist) == 0 and state is None:
        define_net()
        netlist = string_netname()

    if 'default' in netlist:
            netlist.remove('default')
    return netlist


def ina_net():
    netlist = string_netname()
    for net in netlist:
        subprocess.call(['virsh', 'net-destroy', str(net)])
    return netlist


def string_netname_ina():
    netlist = string_netname('ina')
    if len(netlist) == 0:
        netlist = ina_net()
    return netlist


def act_net():
    netlist = string_netname_ina()
    for net in netlist:
        subprocess.call(['virsh', 'net-start', str(net)])
    return netlist


def string_netname_act():
    netlist = string_netname('act')
    if len(netlist) == 0:
        netlist = act_net()
    return netlist


def string_volname(pool=None):
    poollist = []
    vollist = []
    if pool:
        poollist.append(pool)
    else:
        poollist = string_poolname_act()

    for pl in poollist:
        allvol = subprocess.check_output(
            ['virsh', 'vol-list', '--pool', str(pl)]).splitlines()
        if len(allvol) > 2 and re.search('lost+found', allvol[2]):
            del allvol[2]
        del allvol[1]
        del allvol[0]
        for line in allvol:
            vol = line.strip()
            vol = vol.decode('utf-8')
            if vol:
                _, i = re.search(r' +', vol).span()
                vol = vol[i:]
                vollist.append(vol)
    return vollist


def string_xml(xmltype='dom'):
    xmldir = xmltype + 'xml'
    xmllist = []
    dirlist = os.walk(xmldir)[2]
    for fl in dirlist:
        if re.search('.+\.xml', fl):
            xmllist.append(fl)

    return xmllist


def string_xml_doumain_base():
    return '/usr/share/libvirt/schemas/domain.rng'


def cpu_list():
    return re.findall('processor.+?:.+?(\d+)', open('/proc/cpuinfo', 'r').read())


def cpu_count():
    count = []
    for i in range(1, len(cpu_list()) + 1):
        count.append(i)
    return count


def memory():
    mtt = eval(re.findall('MemTotal.*?:.+?(\d+)', open('/proc/meminfo', 'r').read())[0])/1024**2
    memory_list = [x*2 for x in range(1, mtt+1)]
    return memory_list


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
        elif re.search('vol', command):
            otype += '_act'
    elif re.search('network', otype):
        pass
    elif re.search('xml', otype):
        if command in XML_DOMAIN:
            otype += '_domain'
        elif command in XML_NET:
            otype += '_net'
        elif command in XML_POOL:
            otype += '_pool'
        elif command in XML_VOL:
            otype += '_vol'
        elif command in XML_NETFLT:
            otype += '_netflt'
        elif command in XML_IF:
            otype += '_if'
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
