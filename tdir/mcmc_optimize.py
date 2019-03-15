import sys
import numpy as np
import matplotlib.pyplot as plt
import math
from scipy.signal import tukey, fftconvolve, cosine
from mpmath import *
import time
from scipy.stats import norm, multivariate_normal
from astropy import constants as const


start_time = time.time()

def find_nearest(array,value):
    idx = (np.abs(array-value)).argmin()
    return idx,array[idx]

def nearest_two_power(n):

	return pow(2, int(log(n, 2) + 0.5))

#........................................................................................
#...........................MCMC Functions.......................................
#........................................................................................


#...........................CREATING FILTERS.......................................
def filters(L_1_new,L_2_new):
	global D_1
	global D_2
	D_1 = 2*L_1_new*f_s
	D_2 = 2*L_2_new*f_s
	global d_1_frac
	global d_2_frac
	i_1, d_1_frac = divmod(D_1,1)
	i_2, d_2_frac = divmod(D_2,1)

	# delayed filters we're convolving with

	lagrange_1 = np.zeros(len(h_points))
	lagrange_2 = np.zeros(len(h_points))
	h_points_1 = h_points - int(i_1) + 1
	h_points_2 = h_points - int(i_2) + 1
	indices_1 = np.where(np.logical_and(h_points_1>= int(-(number_n-1)/2.0),h_points_1 <= int((number_n-1)/2.0)))
	indices_2 = np.where(np.logical_and(h_points_2>= int(-(number_n-1)/2.0),h_points_2 <= int((number_n-1)/2.0)))

	lagrange_1[indices_2[0]] = [lagrange(int(n),number_n,'two')*np.sinc(int(n)-d_2_frac) for n in h_points_2[indices_2[0]]]
	lagrange_2[indices_1[0]] = [lagrange(int(n),number_n,'one')*np.sinc(int(n)-d_1_frac) for n in h_points_2[indices_2[0]]]

	return lagrange_1, lagrange_2

def generalized_binomial(x,y):
    return math.gamma(x+1) / (math.gamma(y+1) * math.gamma(x-y+1))
#window for LaGrange function WITH MPMATH
def lagrange(n,N,which_D):

	if which_D == 'one':
		D=d_1_frac
	elif which_D == 'two':
		D=d_2_frac
	N = float(N)
	n = float(n) 
	t_D = 0.5*(N-1)+D
	return math.pi*N/(math.sin(math.pi*t_D))*binomial(t_D,N)*binomial((N-1),(n+(N-1)*0.5))

#w_b Blackman function
def blackmann(n,N,which_D):
	if which_D == 'one':
		D=d_1_frac
	elif which_D == 'two':
		D=d_2_frac
	return 0.42 + 0.5*np.cos(2.0*math.pi*(D-n)/float(N-1)) + 0.08*np.cos(4.0*math.pi*(D-n)/float(N-1))

def x_combo(L_1_current,L_2_current):


	lagrange_1,lagrange_2 = filters(L_1_current,L_2_current)

	phi_two_delayed = fftconvolve(downsampled_2,lagrange_2,'same')
	phi_one_delayed = fftconvolve(downsampled_1,lagrange_1,'same')
	#Basic TDI Equation!!!
	x_combo_interp = phi_two_delayed -downsampled_2-phi_one_delayed+downsampled_1
	#not cutting off ends for overlap-add method of generation


	return np.fft.rfft(x_combo_interp,norm='ortho')

def secondary_noise_power(f):

	p_oms = (1.5e-11)**2*(1+np.power(2e-3/f,4))
	p_acc = (3e-15)**2*(1+(0.4e-3/f)**2)*(1+np.power(f/8e-3,4))
	noise_power = p_oms/L_arm**2+2*(1+np.cos(f/f_transfer)**2)*p_acc/(np.power(2*math.pi*f,4)*L_arm**2)
	return noise_power

def likelihood(x_combo_f):
	chi_2 = np.sum(abs(x_combo_f)**2/p_n)
	value = -1/2*chi_2
	return value

def proposal(old_val_1,old_val_2,draw):
	if draw == 0:
		#new_val_1,new_val_2 = np.random.multivariate_normal([old_val_1,old_val_2],(3/const.c.value)**2*np.array([[1,0.99372],[0.99372,1]]))
		new_val_1,new_val_2 = np.random.multivariate_normal([old_val_1,old_val_2],(1/const.c.value)**2*np.array([[1,0.99],[0.99,1]]))

	elif draw ==1:
		#new_val_1,new_val_2 = np.random.multivariate_normal([old_val_1,old_val_2],(1000/const.c.value)**2*np.array([[1,0.99372],[0.99372,1]]))
		new_val_1,new_val_2 = np.random.multivariate_normal([old_val_1,old_val_2],(0.1)**2*np.array([[1,0.99],[0.99,1]]))

		#new_val_1,new_val_2 = np.random.multivariate_normal([old_val_1,old_val_2],(0.01)**2*np.array([[1,0.99372],[0.99372,1]]))
	elif draw == 2:
		new_val_1,new_val_2 = np.random.uniform(low,high),np.random.uniform(low,high)
	else:
		print('error in drawing from one of three proposals.')
		sys.exit()
	return new_val_1,new_val_2
def proposal_prob(mean,val,draw):
	if draw == 0:
		#return multivariate_normal.pdf(val,mean=mean,cov=(3/const.c.value)**2*np.array([[1,0.99372],[0.99372,1]]))
		return multivariate_normal.pdf(val,mean=mean,cov=(1/const.c.value)**2*np.array([[1,0.99],[0.99,1]]))
	elif draw==1 :
		#return multivariate_normal.pdf(val,mean=mean,cov=(1000/const.c.value)**2*np.array([[1,0.99372],[0.99372,1]]))
		return multivariate_normal.pdf(val,mean=mean,cov=(0.1)**2*np.array([[1,0.99],[0.99,1]]))
		#return multivariate_normal.pdf(val,mean=mean,cov=(0.01)**2*np.array([[1,0.99372],[0.99372,1]]))
		#return 1
	elif draw==2 :
		return 1
	else:
		print('error in drawing from one of three proposals.')
		sys.exit()
def prior(val_1,val_2):
	if val_1 >= low and val_1 <= high and val_2 >= low and val_2 <= high:
		return 1
	else:
		return 0
#........................................................................................
#.............................. Raw  PM DATA   ..........................................
#........................................................................................
#Fixed time delays (c = 1)


L_1 = 8.339098
L_2 = 8.339104

f_s = 1

f_samp = 1e6

time_length = 24*3600
number = int(time_length*f_samp)

print(number)
number = nearest_two_power(number)


number_n = 31

f_min = 1e-4 # (= 0.0009765625)
f_max = 1e-1




#................................... Down-Sampled  . ....................................


downsampled_1 = np.genfromtxt('~/Desktop/Project_1/LFN_data/successful_method/d_1_run.dat')
downsampled_2 = np.genfromtxt('~/Desktop/Project_1/LFN_data/successful_method/d_2_run.dat')


#down_sample_factor = int(number/time_length*f_s)
down_sample_factor = int(f_samp/f_s)

#time_ds = times[::down_sample_factor]

length = len(downsampled_1)
print('length downsampled')
print(length)

nearest_number = length
# number points in filter
if nearest_number%2 == 0:
	h_points = np.arange(-nearest_number/2.0,nearest_number/2.0,1)
else:
	h_points = np.arange(-(nearest_number-1)/2.0,(nearest_number-1)/2.0,1)
window = cosine(len(downsampled_2))
ds_1_f = np.fft.rfft(window*downsampled_1,norm='ortho')
ds_2_f = np.fft.rfft(window*downsampled_2,norm='ortho')
#........................................................................................
#...........................MCMC Portion.......................................
#........................................................................................

L_arm = 2.5e9
f_transfer = 3e8/(2*math.pi*L_arm)

#low, high = (L_arm-5e3)/const.c.value,(L_arm+5e3)/const.c.value
low, high = 8.3,8.4

#secondary noise power per bandwidth
f = np.fft.rfftfreq(len(downsampled_1),1/f_s)
p_n = secondary_noise_power(f)
#time mcmc computation time
start_time = time.time()
#for number chain iterations
number_chain = 10000

checkfile = open('chainfile.dat','w')
checkfile.write("#likelihood" + " " + "L_1" + " " + "L_2" + "\n") #column headers"#likelihood L_1 L_2"
k=0

initial_L_1 = np.random.uniform(low,high)
initial_L_2 = np.random.uniform(low,high)

#initial delays accepted into the chain
accept = 1
x_combo_initial = x_combo(initial_L_1,initial_L_2)
print('likelihood')
print(likelihood(x_combo_initial))
old_likelihood = likelihood(x_combo_initial)
checkfile.write(str(old_likelihood) + " " + str(initial_L_1) + " " + str(initial_L_2) + "\n")
old_L_1 = initial_L_1
old_L_2 = initial_L_2


draw_count = 0
#rest of mcmc chain
#for i, j, k in zip(L_1_chain,L_2_chain,counter):
while k <= number_chain:

	print('proposal draw step:')
	print(draw_count)

	print('chain number')
	print(k)

	print('L_1_chain[-1]')
	print(old_L_1)
	print('L_2_chain[-1]')
	print(old_L_2)

	#draw from proposal:
	L_1_draw,L_2_draw = proposal(old_L_1,old_L_2,draw_count)

	print('L_1_draw')
	print(L_1_draw)
	print('L_2_draw')
	print(L_2_draw)
	x_combo_new = x_combo(L_1_draw,L_2_draw)
	new_likelihood = likelihood(x_combo_new)
	print('new_likelihood')
	print(new_likelihood)
	q_top = proposal_prob([L_1_draw,L_2_draw],[old_L_1,old_L_2],draw_count)
	q_bottom = proposal_prob([old_L_1,old_L_2],[L_1_draw,L_2_draw],draw_count)
	alpha = min(np.log(prior(L_1_draw,L_2_draw))+new_likelihood+np.log(q_top)-np.log(prior(old_L_1,old_L_2))-old_likelihood-np.log(q_bottom),0)
	u = np.log(np.random.uniform(0.000,1.000))
	print('alpha')
	print(alpha)
	print('u')
	print(u)

	if alpha >= u:
		old_L_1 = L_1_draw  #L_1_chain = np.append(L_1_chain,L_1_draw)
		old_L_2 = L_2_draw
		old_likelihood = new_likelihood
		checkfile.write(str(old_likelihood) + " " + str(old_L_1) + " " + str(old_L_2) + "\n")
		accept+=1

	elif (alpha < u):
		checkfile.write(str(old_likelihood) + " " + str(old_L_1) + " " + str(old_L_2) + "\n")

	else:
		print('something wrong in acceptance/rejection step')

	k+=1
	if draw_count == 0 or draw_count ==1:
		draw_count+=1
	elif draw_count == 2:
		draw_count = 0	

checkfile.close()


print("--- %s seconds ---" % (time.time() - start_time))


print('L_1 True')
print(L_1)
print('L_2 True')
print(L_2)

print('acceptance ratio')
print(accept/number_chain)

print('number accepted')
print(accept)





