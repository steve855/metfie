"""calc.py: Classes for EOS and gun simulation.  Derived from calc.py
in parent directory.

Run using python3.

"""
import numpy as np
from scipy.integrate import quad, odeint
import scipy.interpolate #.InterpolatedUnivariateSpline
#https://github.com/scipy/scipy/blob/v0.14.0/scipy/interpolate/fitpack2.py
class spline(scipy.interpolate.InterpolatedUnivariateSpline):
    '''From the source:

    data = dfitpack.fpcurf0(x,y,k,w=w,xb=bbox[0],xe=bbox[1],s=s)
    n,t,c,k,ier = data[7],data[8],data[9],data[5],data[-1]
    self._eval_args = t[:n],c[:n],k
    
    t is the array of knots, c is the array of coefficients and k is the
    order.    
    '''
    def get_t(self):
        return self._eval_args[0]
    def get_c(self):
        return self._eval_args[1]
    def set_c(self,c):
        self._eval_args = self._eval_args[0], c, self._eval_args[2]
        return
class GUN(object):
    def __init__(self,      # GUN instance
                 C=2.56e10, # Constant in nominal equation of state
                 xi=0.4,    # Initial position of projectile / cm
                 xf=4.0,    # Final/muzzle position of projectile /cm
                 m=100.0,   # Mass of projectile / g
                 N=400,     # Number of intervals between xi and xf
                 ):
        self.C = C
        self.xi = xi
        self.xf = xf
        self.m = m
        self._set_N(N)
        return
    def _set_N(self,  # GUN instance
               N,     # Number of intervals between xi and xf
               ):
        '''Interval lengths are uniform on a log scale ie constant ratio.  x_c
        are points in the centers of the intervals and x are the end
        points.

        '''
        # N+1 points and N intervals equal spacing on log scale
        log_x = np.linspace(np.log(self.xi),np.log(self.xf),N+1)
        step = (log_x[-1] - log_x[0])/N
        assert len(log_x) == N+1
        log_c = log_x[:-1] + step/2
        self.x = np.exp(log_x)
        self.x_c = np.exp(log_c) # Centers of intervals on log scale
        self.dx = self.x[1:] - self.x[:-1]
        self.eos = lambda t: self.C/t**3
        self.s =self.eos(self.x_c)  # Nominal eos at sample points
        def dT_dx(t, x):
            ''' a service function called by odeint to calculate
            muzzle time T.  Since odeint calls dT_dx with two
            arguments, dT_dx has the unused t argument.
            '''
            # Since self.E(self.xi) = 0, I put a floor of self.x_c[0] on x
            x = max(x,self.x_c[0])
            x = min(x,self.xf)
            return np.sqrt((self.m/(2*self.E(x))))
        self.dT_dx = dT_dx
        return
    def E(self, # GUN instance
          x     # Scalar position at which to calculate energy
          ):
        ''' Integrate eos between xi and x using numpy.integrate.quad
        to get energy of projectile at position.
        '''
        rv, err = quad(self.eos,self.xi,x)
        return rv
    def x_dot(self, # GUN instance
              x     # Position[s] /cm at which to calculate velocity
              ):
        ''' Calculate the projectile velocity at position x
        '''
        if isinstance(x,np.ndarray):
            return np.array([self.x_dot(x_) for x_ in x])
        elif isinstance(x,np.float): 
            return np.sqrt(2*self.E(x)/self.m)
        else:
            raise RuntimeError('x has type %s'%(type(x),))
    def T(self,  # GUN instance
          x      # Array of positions /cm at which to calculate time
          ):
        ''' Calculate projectile time as a function of position
        '''
        rv = odeint(self.dT_dx, # RHS of ODE
                         0,     # Initial value of time
                         x,     # Solve for time at each position in x
                         )
        return rv.flatten()
    def set_eos(self,   # GUN instance
                x,
                f
                ):
        self.eos = spline(x, f)
        return
    def log_like(
            self, # GUN instance
            t,    # Array of measured times
            v     # Array of measured velocities
            ):
        ''' Assume t are accurate and that for model velocities m
            log(p(v|m)) =\sum_t -((v-m)/1e5)^2
        '''
        t_ = self.T(self.x)
        x_t = spline(t_,self.x)
        x = x_t(t)
        m = self.x_dot(x)
        d = (v-m)/1e5
        return -np.dot(d,d),-2*d
    def dv_df(
            self, # GUN instance
            x_v,  # Positions of velocity measuerments
            x_f,  # Positions of eos specifications
            fraction=1.0e-2
            ):
        '''Derivative of velocity at points x wrt. self.f at points x_f.
        Returns a len(x_v) \times len(x_f) matrix.
        
        '''
        eos_orig = self.eos
        f_x_nom = np.array([self.eos(x) for x in x_f])
        self.set_eos(x_f, f_x_nom)
        f_all_nom = self.eos(self.x) # Use spline as reference
        v_x_nom = self.x_dot(x_v)
        f = self.eos
        f_nom_c = f.get_c()
        f_nom_t = f.get_t()
        # f_nom_t is 4 longer than x_f but matches x_f[2:-2] in the middle
        rv = np.zeros((len(x_v), len(f_nom_c)))
        
        # For debug plots: f_i, df_i, v_i
        f_i = np.empty((len(f_nom_c),len(self.x)))
        v_i = np.empty((len(f_nom_c),len(x_v)))

        # Should pick pertubations that maintain convexity
        D_f = np.empty(f_nom_c.shape)
        for i in range(len(f_nom_c)):
            f_c = f_nom_c.copy()
            D_f[i] = f_c[i]*fraction
            if D_f[i] == 0.0:
                D_f[i] = D_f[i-1]
            f_c[i] += D_f[i]
            f.set_c(f_c)
            v = self.x_dot(x_v)
            Dv_Df = (v - v_x_nom)/D_f[i]
            rv[:,i] = Dv_Df
            # Debug data
            f_i[i,:] = f(self.x)
            v_i[i,:] = v
        self.eos = eos_orig
        return f_i, v_i, f_all_nom, v_x_nom, rv
def plot_f_v_dL(gun, gun_p, fig):
    '''Calculate and plot nominal and perturbed eoses and the consequent
    velocities.  Also plot the gradient of the log likelihood.
    '''
    # Calculate v(t) and f(x) for perturbed gun
    t = gun.T(gun.x)
    v_p = np.array([gun_p.x_dot(x) for x in gun.x])
    L,dL = gun.log_like(t,v_p)
    v_p /= 1e5 # km/s
    f_p = [gun_p.eos(x) for x in gun.x]
    f = [gun.eos(x) for x in gun.x]
    t *= 1e6 # microseconds
    v = gun.x_dot(gun.x)/1e5 # km/s
    nom = r'$\rm nominal$'
    pert = r'$\rm perturbed$'
    for n_,xy,l_x,l_y,loc in (
            (1,((gun.x,f,nom),(gun.x,f_p,pert)),r'$x$',r'$f$','upper right'),
            (2,((t,v,nom),(t,v_p,pert)),r'$t$',r'$v$','lower right'),
            (3,((t,dL,None),),r'$t$',r'$dL$','upper right'),
            ):
        ax = fig.add_subplot(3,1,n_)
        ax.set_ylabel(l_y)
        ax.set_xlabel(l_x)
        for x_,y_,l_ in xy:
            ax.plot(x_,y_,label=l_)
        ax.legend(loc=loc)
def plot_dv_df(gun, x, DA, DB, fig):
    '''Plot analysis of 2 finite difference approximations to dv/df
    '''
    f_i_A, v_i_A, f_all_nom_A, v_x_nom_A, Dv_Df_A = DA
    f_i_B, v_i_B, f_all_nom_B, v_x_nom_B, Dv_Df_B = DB

    n_i, n_x = f_i_A.shape
    # Positions for add_subplot(4,3,n_)
    #  1  2  3
    #  4  5  6
    #  7  8  9
    # 10 11 12
    for n_,x_,y_,l_ in (
            (1,gun.x,f_i_B,'$f$'),
            (2,gun.x,f_i_B-f_all_nom_B,'$Df$'),
            (3,gun.x,f_i_A-f_all_nom_A,'$Df$'),
            (4,x,v_i_B,'$v$'),
            (5,x,v_i_B-v_x_nom_B,'$Dv$'),
            (6,x,v_i_A-v_x_nom_A,'$Dv$'),
            (7,x,Dv_Df_B.T-Dv_Df_A.T,r'$\rm Difference$'),
            (8,x,Dv_Df_B.T,'$Dv/Df$'),
            (9,x,Dv_Df_A.T,'$Dv/Df$'),
            (11,x,v_i_B*v_i_B-v_x_nom_B*v_x_nom_B,'$DE$'),
            (12,x,v_i_A*v_i_A-v_x_nom_A*v_x_nom_A,'$DE$'),
            ):
        ax = fig.add_subplot(4,3,n_)
        ax.set_ylabel(l_)
        ax.set_xlabel('$x$')
        for i in range(n_i):
            ax.plot(gun.x, y_[i])
        
def main():
    ''' Diagnostic plots
    '''
    from matplotlib import cm
    from matplotlib.ticker import LinearLocator, FormatStrFormatter
    import matplotlib.pyplot as plt
    
    # Unperturbed gun
    gun = GUN()

    # Select samples in x for derivative and perturbation
    n = 10
    log_x = np.linspace(np.log(gun.xi),np.log(gun.xf),n)
    x = np.exp(log_x)
    
    # Create perturbed gun
    f = gun.eos(x)
    x_off = 0.6
    y = x-x_off
    freq=.2
    w = .2
    D = np.sin(freq*y)*np.exp(-y**2/(2*w**2))*gun.eos(x_off)/freq
    gun_p = GUN()
    gun_p.set_eos(x,f+D)
    
    #fig1 = plt.figure(figsize=(8,10))
    #plot_f_v_dL(gun, gun_p, fig1)

    # Calculate derivatives
    # fraction = 2.0e-2 about max for convex f(x)
    # fraction = 1.0e-3 about min for bugless v(x) integration
    DA = gun.dv_df(gun.x, x, 2.0e-3)
    DB = gun.dv_df(gun.x, x, 2.0e-2)
    fig2 = plt.figure(figsize=(14,16))
    plot_dv_df(gun, x, DA, DB, fig2)
    plt.show()
    #fig.savefig('fig.pdf', format='pdf')
    
if __name__ == "__main__":
    main()
    #_test()

#---------------
# Local Variables:
# mode: python
# End:
