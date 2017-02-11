from dice.core import item
from dice import utils
# from . import virsh


class Item(item.ItemBase):
    def run(self):
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
                cmdline += ' %s' % arg
        self.res = utils.run(cmdline)
