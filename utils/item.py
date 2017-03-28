from dice.core import item
from dice import utils
import re


class Item(item.ItemBase):
    def run(self):
        def replacexml(self, xml=None):
            f = open(xml, 'r')
            lines = f.readline()
            f.close()
            for line in lines:
                ymlname = re.findall(r"'(yaml_.+)'", line)
                if ymlname is not None:
                    ymlvalue = self.get(ymlname)
                    ymlvalue = utils.escape(str(ymlvalue))
                    line = line.replace(ymlname, ymlvalue)

            f = open(xml, 'w')
            f.writelines(lines)

        cmdline = 'virsh'
        cmd = utils.escape(str(self.get('subcmd')))
        cmdline += ' %s' % cmd

        options = self.get('options')
        if options is not None:
            for opt in options:
                cmdline += ' --%s' % utils.escape(str(opt))
                opt = str(opt) + '_arg'
                opt = opt.replace('-', '_')
                arg = self.get(opt)

                if arg is None:
                    arg = ''
                arg = utils.escape(str(arg))
                if re.search('xmlname', arg):
                    replacexml(self, arg)
                cmdline += ' %s' % arg
        f = open('runlog', 'a')
        f.write(cmdline + '\n')
        f.close()
        self.res = utils.run(cmdline)
