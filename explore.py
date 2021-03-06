import sys
import numpy as np
import matplotlib as mpl
DEBUG = False
def plot_eig(L, floor, ax, args):
    g,h = L.gh(args.m_g, args.m_h)
    G,H = np.meshgrid(g, h)
    b = np.log10(np.fmax(L.eigenvector, floor))
    z = L.vec2z(b, g, h, np.log10(floor))
    surf = ax.plot_surface(
        G, H, z.T, rstride=1, cstride=1, cmap=mpl.cm.jet, linewidth=1,
        antialiased=False)
    ax.set_xlabel(r'$g$')
    ax.set_ylabel(r'$h$')
    ax.set_title(r'$n_g=%d$ $n_h=%d$ $dy=%8.3g$ $\lambda=%8.3g$'%(
        L.n_g, L.n_h, L.dy, L.eigenvalue))

def main(argv=None):
    '''For looking at sensitivity of time and results to u, dy, n_g, n_h.

    '''
    import argparse
    global DEBUG
    if argv is None:                    # Usual case
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description='Plot eigenfunction of the integral equation')
    parser.add_argument('--u', type=float, default=(2.0e-5),
                       help='log fractional deviation')
    parser.add_argument('--dy', type=float, default=3.2e-4,
                       help='y_1-y_0 = log(x_1/x_0)')
    parser.add_argument('--n_g', type=int, default=200,
                       help='number of integration elements in value')
    parser.add_argument('--n_h', type=int, default=200,
help='number of integration elements in slope.  Require n_h > 192 u/(dy^2).')
    parser.add_argument('--m_g', type=int, default=50,
                       help='number of points for plot in g direction')
    parser.add_argument('--m_h', type=int, default=50,
                       help='number of points for plot in h direction')
    parser.add_argument('--eigenvalue', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--eigenfunction', type=str, default=None,
        help="Calculate eigenfunction and write to this file")
    parser.add_argument('--Av', type=str, default=None,
        help="Illustrate A applied to some points and write to this file")
    args = parser.parse_args(argv)
    if args.Av == None and args.eigenfunction == None and not args.eigenvalue:
        print('Nothing to do')
        return 0
    params = {'axes.labelsize': 18,     # Plotting parameters for latex
              'text.fontsize': 15,
              'legend.fontsize': 15,
              'text.usetex': True,
              'font.family':'serif',
              'font.serif':'Computer Modern Roman',
              'xtick.labelsize': 15,
              'ytick.labelsize': 15}
    mpl.rcParams.update(params)
    if args.debug:
        DEBUG = True
        mpl.rcParams['text.usetex'] = False
    else:
        mpl.use('PDF')
    import matplotlib.pyplot as plt  # must be after mpl.use
    from scipy.sparse.linalg import LinearOperator
    from mpl_toolkits.mplot3d import Axes3D  # Mysteriously necessary
                                             #for "projection='3d'".
    from matplotlib import cm
    from matplotlib.ticker import LinearLocator, FormatStrFormatter
    from first_c import LO_step
    #from first import LO_step   # Factor of 9 slower

    g_step = 2*args.u/(args.n_g-1)
    h_max = (24*args.u)**.5
    h_step = 2*h_max/(args.n_h-1)
    A = LO_step( args.u, args.dy, g_step, h_step)
    if args.eigenvalue:
        from scipy.sparse.linalg import eigs as sparse_eigs
        from numpy.linalg import norm
        tol = 1e-10
        w,b = sparse_eigs(A,  tol=tol, k=10)
        print('Eigenvalues from scipy.sparse.linalg.eigs:')
        for val in w:
            print('norm:%e,  %s'%(norm(val), val))
        A.power(small=tol)
        print('From A.power() %e'%(A.eigenvalue,))
    if args.eigenfunction != None:
        # Calculate and plot the eigenfunction
        tol = 5e-6
        maxiter = 1000
        A.power(small=tol, n_iter=maxiter, verbose=True)
        floor = 1e-20*max(A.eigenvector).max()
        fig = plt.figure(figsize=(24,12))
        ax1 = fig.add_subplot(1,2,1, projection='3d', elev=15, azim=135)
        ax2 = fig.add_subplot(1,2,2, projection='3d', elev=15, azim=45)
        plot_eig(A, floor, ax1, args)
        plot_eig(A, floor, ax2, args)
        if not DEBUG:
                fig.savefig( open(args.eigenfunction, 'wb'), format='pdf')
    if DEBUG:
        plt.show()
    return 0

if __name__ == "__main__":
    rv = main()
    sys.exit(rv)

#---------------
# Local Variables:
# mode: python
# End:
