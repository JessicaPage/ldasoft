/*********************************************************/
/*                                                       */
/*        Bright_Remove.c, Version 2.3, 4/28/2011        */
/*      Written by Neil Cornish & Tyson Littenberg       */
/*                                                       */
/* gcc -O2 -o Full_Residual Full_Residual.c Subroutines.c arrays.c -lm -lgsl */
/*                                                       */
/*********************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "arrays.h"
#include "Constants.h"
#include "Detector.h"
#include "Subroutines.h"


int main(int argc,char **argv)
{
  
  double f, fdot, theta, phi, A, iota, psi, phase;
  char Gfile[50];
  double *params;
  double *XfLS, *AALS, *EELS;
  double *XLS, *AA, *EE;
  long M, N, q;
  long i, k, cnt, cc1, mult, imax, imin;
  double sqT;
  double *Xnoise, *Xconf;
  double *AEnoise, *AEconf;
  double *XP, *AEP;
  
  FILE* Infile;
  FILE* Outfile;
  FILE* Abright;
  
  if(argc !=4) KILL("Full_Residual XAE.dat BrightAE.dat Orbit.dat\n");
  
  printf("***********************************************************************\n");
  printf("*\n");
  printf("* FisherGalaxy: Residual Tool\n");
  printf("*   Simulated Data:         %s\n",argv[1]);
  printf("*   AE Candidate Sources:   %s\n",argv[2]);
  printf("*   Orbit File:             %s\n",argv[3]);

  /* Figure out TOBS and NFFT */
  Infile = fopen(argv[1],"r");
  double junk;
  double f1,f2;
  fscanf(Infile,"%lf%lf%lf%lf%lf%lf%lf\n", &f1, &junk, &junk, &junk, &junk, &junk, &junk);
  fscanf(Infile,"%lf%lf%lf%lf%lf%lf%lf\n", &f2, &junk, &junk, &junk, &junk, &junk, &junk);
  double TOBS = 1./(f2-f1);
  int    NFFT = (int)floor(TOBS*DT);
  fclose(Infile);
  /*****************************/
  
  printf("*   Observing Time:         %.1f year (%f s)\n",TOBS/year,TOBS);
  printf("*\n");
  printf("***********************************************************************\n");
  
  Abright = fopen(argv[2],"r");
  
  //Data structure for interpolating orbits from file
  struct lisa_orbit *LISAorbit;
  LISAorbit = &orbit;
  
  //Set up orbit structure (allocate memory, read file, cubic spline)
  sprintf(Gfile,"%s",argv[3]);
  initialize_orbit(Gfile, LISAorbit);
  
  params = dvector(0,9);
  
  if((TOBS/year) <= 8.0) mult = 8;
  if((TOBS/year) <= 4.0) mult = 4;
  if((TOBS/year) <= 2.0) mult = 2;
  if((TOBS/year) <= 1.0) mult = 1;
  
  XfLS = dvector(0,NFFT-1);  AALS = dvector(0,NFFT-1);  EELS = dvector(0,NFFT-1);
  
  for(i=0; i<NFFT; i++)
  {
    XfLS[i] = 0.0;
    AALS[i] = 0.0;
    EELS[i] = 0.0;
  }
  
  imax = (long)ceil(4.0e-2*TOBS);
  imin = (long)floor(1.0e-4*TOBS);
  sqT = sqrt(TOBS);

  printf("Reading Data File\n");

  Infile = fopen(argv[1],"r");
  for(i=1; i< imax; i++)
  {
    fscanf(Infile,"%lf%lf%lf%lf%lf%lf%lf\n", &f, &XfLS[2*i], &XfLS[2*i+1],
           &AALS[2*i], &AALS[2*i+1], &EELS[2*i], &EELS[2*i+1]);
  }
  fclose(Infile);
  
  printf("Starting Removal\n");
  
  cnt = 0;
  cc1 = 0;
  
  //count lines in file
  int NSIM;
  
  
  /********************************************************/
  /* AE CHANNELS                                          */
  /********************************************************/

  printf("Cleaning AE-channel Data\n");
  
  NSIM = 0;
  while ( !feof(Abright) )
  {
    fscanf(Abright, "%lf%lf%lf%lf%lf%lf%lf%lf\n", &f, &fdot, &theta, &phi, &A, &iota, &psi, &phase);
    NSIM++;
  }
  rewind(Abright);
  NSIM--;
  
  printf("Removing %i bright sources\n",NSIM);
  
  for(int n=0; n<NSIM; n++)
  {
    if(n%(NSIM/100)==0)printProgress((double)n/(double)NSIM);
    
    fscanf(Abright, "%lf%lf%lf%lf%lf%lf%lf%lf\n", &f, &fdot, &theta, &phi, &A, &iota, &psi, &phase);
    
    params[0] = f;
    params[1] = 0.5*pi-theta;
    params[2] = phi;
    params[3] = A;
    params[4] = iota;
    params[5] = psi;
    params[6] = phase;
    params[7] = fdot;
    params[8] = 11.0/3.0*fdot*fdot/f;
    
    N = 32*mult;
    if(f > 0.001) N = 64*mult;
    if(f > 0.01) N = 256*mult;
    if(f > 0.03) N = 512*mult;
    if(f > 0.1) N = 1024*mult;

    q = (long)(f*TOBS);
    
    M = galactic_binary_bandwidth(LISAorbit->L, LISAorbit->fstar, f, fdot, cos(params[1]), params[3], TOBS, N);
    
    XLS = dvector(1,2*M);
    AA  = dvector(1,2*M);
    EE  = dvector(1,2*M);
    
    FAST_LISA(LISAorbit, TOBS, params, N, M, XLS, AA, EE);
    
    for(i=1; i<=M; i++)
    {
      k = (q + i -1 - M/2);
      if(k>0)
      {
        AALS[2*k]   -= sqT*AA[2*i-1];
        AALS[2*k+1] -= sqT*AA[2*i];
        EELS[2*k]   -= sqT*EE[2*i-1];
        EELS[2*k+1] -= sqT*EE[2*i];
//        AALS[2*k]   += sqT*AA[2*i-1];
//        AALS[2*k+1] += sqT*AA[2*i];
//        EELS[2*k]   += sqT*EE[2*i-1];
//        EELS[2*k+1] += sqT*EE[2*i];
      }
    }
    
    free_dvector(XLS,1,2*M);
    free_dvector(AA,1,2*M);
    free_dvector(EE,1,2*M);
  }
  printProgress(1.0);

  
  printf("\nRemoval Finished\n");
  
  
  Outfile = fopen("Galaxy_AE_Residual.dat","w");
  for(i=1; i< imax; i++)
  {
    f = (double)(i)/TOBS;
    fprintf(Outfile,"%.12g %e %e %e %e\n", f, AALS[2*i], AALS[2*i+1], EELS[2*i], EELS[2*i+1]);
  }
  fclose(Outfile);
  
  XP = dvector(0,NFFT/2);  AEP = dvector(0,NFFT/2);
  Xnoise = dvector(0,NFFT/2);  Xconf = dvector(0,NFFT/2);
  AEnoise = dvector(0,NFFT/2);  AEconf = dvector(0,NFFT/2);
  
  for(i=0; i<NFFT/2; i++)
  {
    XP[i] = (2.0*(XfLS[2*i]*XfLS[2*i] + XfLS[2*i+1]*XfLS[2*i+1]));
    AEP[i] = (2.0*(AALS[2*i]*AALS[2*i]+AALS[2*i+1]*AALS[2*i+1]));
    instrument_noise((double)i/TOBS, LISAorbit->fstar, LISAorbit->L, &AEnoise[i], &Xnoise[i]);
  }
  printf("Estimate Confusion Noise\n");

  //medianAE(imin, imax, LISAorbit->fstar, LISAorbit->L, AEP, AEnoise, AEconf, TOBS);
  int divs = 100;  // must be even - used to compute median
  
  if(divs/2+1 > imin) imin = divs/2+1;
  if(imax > NFFT/2-divs/2-1) imax =  NFFT/2-divs/2-1;
  
  //spline_fit(1, divs, imin, imax, AEP, AEnoise, AEconf, TOBS, LISAorbit->fstar,LISAorbit->L);
  
  confusion_mcmc(AEP, AEnoise, AEconf, (int)floor(0.0001*TOBS), (int)floor(0.006*TOBS), TOBS);

  printf("Writing Residual File\n");

  Outfile = fopen("Confusion_AE_Residual.dat","w");
  for(i=imin; i<= imax; i++)
  {
    f = (double)(i)/TOBS;
    fprintf(Outfile,"%.12g %e %e\n", f, AEnoise[i], AEconf[i]);
  }
  fclose(Outfile);
  
  Outfile = fopen("Confusion_AE_Residual_DS.dat","w");
  for(i=imin; i<= imax; i++)
  {
    if(i%100==0)
    {
      f = (double)(i)/TOBS;
      fprintf(Outfile,"%.12g %e %e\n", f, AEnoise[i], AEconf[i]);
    }
  }
  fclose(Outfile);
  
  return 0;
  
}


