import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import sys

class FigManager(object):

    def __init__(self, fn='', exts=['svg', 'pdf', 'png', 'eps'], show=False, nrows=1, ncols=1, 
                 figsize=(18,12), tight_layout=True,
                 sns_style='whitegrid', quiet=True, **fig_kwds):
        self.quiet = quiet
        if not self.quiet and plt.gcf():
            print >>sys.stderr, 'leaving context of', repr(plt.gcf())
        
        sns.set_style(sns_style)
        self.fig, self.ax = plt.subplots(nrows=nrows, ncols=ncols, 
                                         figsize=figsize, tight_layout=tight_layout, **fig_kwds)
        
        self.fn = fn
        self.exts = exts
        self.show = show
        
        assert self.fig == plt.gcf()
    
    def __enter__(self):
        return self.fig, self.ax
    
    def __exit__(self, t, v, tb):
        if t is not None:
            print >>sys.stderr, 'ERROR', t, v, tb
        
        if self.fn:
            if not self.quiet:
                print >>sys.stderr, 'saving figure', repr(self.fig)
            for ext in self.exts:
                self.fig.savefig('{}.{}'.format(self.fn, ext))
        
        if self.show:
            assert self.fig == plt.gcf()
            if not self.quiet:
                print >>sys.stderr, 'showing figure', repr(self.fig)
            plt.show(self.fig)

        if not self.quiet:
            print >>sys.stderr, 'closing figure', repr(self.fig)
        #if type(self.ax) is np.ndarray:
        #    for i in enumerate(ax):
        #        self.fig.delaxes(self.ax[i])
        #else:
        #    self.fig.delaxes(self.ax)
        plt.close(self.fig)
        del self.ax
        del self.fig
        if not self.quiet:
            print >>sys.stderr, 'returning context to', repr(plt.gcf())
