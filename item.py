from dice.core import item
from dice import utils


class Item(item.ItemBase):
    def run(self):
        cmdline = 'virsh'
        cmdline += ' %s' % utils.escape(str(self.get('subcmd')))
        options = self.get('options')
        if options is not None:
            for opt in options:
                cmdline += ' --%s' % utils.escape(str(opt))
        self.res = utils.run(cmdline)
