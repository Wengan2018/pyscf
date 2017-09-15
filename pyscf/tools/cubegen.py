#!/usr/bin/env python
#
# Author: Qiming Sun <osirpt.sun@gmail.com>
#

import numpy
import time
import pyscf
from pyscf import lib
from pyscf.dft import numint, gen_grid

'''
Gaussian cube file format
'''

def density(mol, outfile, dm, nx=80, ny=80, nz=80):
  from pyscf.tools.m_cube import cube_c
  """Calculates electron density.
    Args:
        mol (Mole): Molecule to calculate the electron density for.
        outfile (str): Name of Cube file to be written.
        dm (ndarray): Density matrix of molecule.
        nx (int): Number of grid point divisions in x direction.
           Note this is function of the molecule's size; a larger molecule
           will have a coarser representation than a smaller one for the
           same value.
        ny (int): Number of grid point divisions in y direction.
        nz (int): Number of grid point divisions in z direction.
  """
  
  cc = cube_c(mol, nx=nx, ny=ny, nz=nz) # Initialize the class cube_c
    
  # Compute density on the .cube grid
  coords = cc.get_coords()
  ngrids = cc.get_ngrids()
  blksize = min(8000, ngrids)
  rho = numpy.empty(ngrids)
  ao = None
  for ip0, ip1 in gen_grid.prange(0, ngrids, blksize):
    ao = numint.eval_ao(mol, coords[ip0:ip1], out=ao)
    rho[ip0:ip1] = numint.eval_rho(mol, ao, dm)
  rho = rho.reshape(cc.nx,cc.ny,cc.nz)
    
  cc.write(rho, outfile, comment='Electron density in real space (e/Bohr^3)')   # Write out density to the .cube file


def mep(mol, outfile, dm, nx=80, ny=80, nz=80):
    from pyscf.tools.m_cube import cube_c
    """Calculates the molecular electrostatic potential (MEP).

    Args:
        mol (Mole): Molecule to calculate the MEP for.
        outfile (str): Name of Cube file to be written.
        dm (str): Density matrix of molecule.
        nx (int): Number of grid point divisions in x direction.
           Note this is function of the molecule's size; a larger molecule
           will have a coarser representation than a smaller one for the
           same value.
        ny (int): Number of grid point divisions in y direction.
        nz (int): Number of grid point divisions in z direction.
    """
    cc = cube_c(mol, nx=nx, ny=ny, nz=nz)

    coords = cc.get_coords()
    
    # Nuclear potential at given points
    Vnuc = 0
    for i in range(mol.natm):
       r = mol.atom_coord(i)
       Z = mol.atom_charge(i)
       rp = r - coords
       Vnuc += Z / numpy.einsum('xi,xi->x', rp, rp)**.5

    # Potential of electron density
    Vele = []
    for p in coords:
        mol.set_rinv_orig_(p)
        Vele.append(numpy.einsum('ij,ij', mol.intor('cint1e_rinv_sph'), dm))

    MEP = Vnuc - Vele     # MEP at each point

    MEP = numpy.asarray(MEP)
    MEP = MEP.reshape(nx,ny,nz)

    cc.write(MEP, outfile, 'Molecular electrostatic potential in real space')     # Write the potential
    
if __name__ == '__main__':
    from pyscf import gto, scf
    from pyscf.tools import cubegen
    mol = gto.M(atom='O 0.00000000,  0.000000,  0.000000; H 0.761561, 0.478993, 0.00000000,; H -0.761561, 0.478993, 0.00000000,', basis='6-31g*')
    mf = scf.RHF(mol)
    mf.scf()
    cubegen.density(mol, 'h2o_den.cube', mf.make_rdm1())
    cubegen.mep(mol, 'h2o_pot.cube', mf.make_rdm1())

