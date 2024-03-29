"""
Portion of the code used here was retrieved from an example use of SimComponents to simulate a packet queue with M/M/1 characteristics.
Copyright 2014 Dr. Greg M. Bernstein
Released under the MIT license
"""
import random
import functools
from datetime import datetime
import time
import simpy
from datetime import datetime, timedelta
#import matplotlib.pyplot as plt
from SimComponents import PacketGenerator, PacketSink, SwitchPort, PortMonitor
import numpy as np
import pandas as pd
import scipy.io
import csv
import threading
from csv import writer
import matplotlib.pyplot as plt
#####################################################################################
 
#####################################################################################
#Global variable definition
time_s=datetime.now() 
time_e=datetime.now()
def Measurements(FB,TB,IAT,TD,PC,RTT,avqs,so,AR,pd,Time,sample):
    list_column=["FB","TB","IAT","TD","Arrival Time","PC","Packet Size","Acknowledgement Packet Size","RTT","Average Queu Size","System Occupancy","Arrival Rate","Service Rate","Packet Dropped","Time","sample"]
    list_row=[]
#to create a list full of rows as the writerow function reads data row-wise
    for i in range(len(IAT)):
        list_temp=[FB[i],TB[i],IAT[i],TD[i],ATm[i],PC[i],PACKSZ[i],ACKSZ[i],RTT[i],avqs[i],so[i],AR[i],SR[i],pd[i],Time[i],sample[i]]
        list_row.append(list_temp)
 
        
    with open ("Sharon2.csv", 'w', newline="") as entry:
        writer=csv.writer(entry)
        writer.writerow(list_column)
        writer.writerows(list_row)
 
        entry.close()
"""def ARdistributions(AR):
    list_column=["AR"]
    list_row=[]
 
#to create a list full of rows as the writerow function reads data row-wise
    for i in range(len(AR)):
        list_temp=[AR[i]]
        list_row.append(list_temp)
 
        
    with open ("ARdist.csv", 'w', newline="") as entry:
        writer=csv.writer(entry)
        writer.writerow(list_column)
        writer.writerows(list_row)
 
        entry.close()"""
 
def iatdistributions(iatd):
    list_column=["IATD"]
    list_row=[]
 
#to create a list full of rows as the writerow function reads data row-wise
    for i in range(len(iatd)): 
        list_temp=[iatd[i]]
        list_row.append(list_temp)
 
        
    with open ("iatdist.csv", 'w', newline="") as entry:
        writer=csv.writer(entry)
        writer.writerow(list_column)
        writer.writerows(list_row)
 
        entry.close()
def sampling(sampletime,sample):
    #i=0
    s=1
    #sample.append(s)
    p=sampletime[0]
   # while(i<len(sampletime)):
    for i in range(len(sampletime)):
        if(sampletime[i]-p>0.125):
            s=s+1
            p=sampletime[i]
        sample.append(s)
        #i=i+1
"""           
def histograms(of):
    fig, axis = plt.subplots()
    axis.hist(of, bins=100, normed=True)
    axis.set_title("Histogram for Sink Interarrival times")
    axis.set_xlabel("time")
    axis.set_ylabel("normalized frequency of occurrence")
     # fig.savefig("ArrivalHistogram.png")
    plt.show()   
    """
#####################################################################################
 
#####################################################################################
# Set up arrival and packet size distributions
# Creating functions to be called during execution of the simulation
# Each call to these will produce a new random value.
 
# exponential arrival distribution for generator 
adistl = np.zeros(shape=(1000))
for i in range(1000):
    adistl[i] = random.expovariate(0.5)
def adist():  
     #adist = functools.partial(random.expovariate, 10)
    return random.choice(adistl)
 
adist_listACK = np.zeros(shape=(1000))
for i in range(1000):
    adist_listACK[i] = random.expovariate(0.0064)
def adistACK():  
     #adist = functools.partial(random.expovariate, 10)
    return random.choice(adist_listACK)
 
# mean size 100 bytes
sdist_list = np.zeros(shape=(1000))
for i in range(1000):
    sdist_list[i] = random.expovariate(0.1)
def sdist(): 
     #sdist = functools.partial(random.expovariate, 0.1)  
    return random.choice(sdist_list)
 
sdistL = np.zeros(shape=(1000))
for i in range(1000):
    sdistL[i] = 1300
def sdistL(): 
     #sdist = functools.partial(random.expovariate, 0.1)  
    return random.choice(sdist_list)
 
sdistLack = np.zeros(shape=(1000))
for i in range(1000):
    sdistLack[i] = 64
def sdistLack(): 
     #sdist = functools.partial(random.expovariate, 0.1)  
    return random.choice(sdist_list)
samp_dist_list = np.zeros(shape=(1000))
for i in range(1000):
    samp_dist_list[i] = random.expovariate(1.0)
def samp_dist():
    #samp_dist = functools.partial(random.expovariate, 1.0)
    return random.choice(samp_dist_list)
 
#Connect node to another node
#def connect_node(Exnode, Newnode):
 
def b1ping():
    j=1
    while(j<=n):
        if(1!=j):
          print("From Bus", 1 ," to Bus",j)
          #a=adist()
          #samptime,time,rtt,td,iat,pr,PS=Rhop1(adist,sdistL,sdistLack,time_s,time_e,sampl) 
          sr,acksz,packsz,AT,AVQS,SO,ar,samptime,time,rtt,td,iat,pr,PD=Rhop1(sdistL,sdistLack,time_s,time_e,sampl)          
          SR.append(sr) 
          ACKSZ.append(acksz)
          PACKSZ.append(packsz)
          ATm.append(AT) 
          AR.append(ar)
          so.append(SO)
          RTT.append(rtt)
          TD.append(td)
          IAT.append(iat)
          PR.append(pr)
          Time.append(time)
          sampletime.append(samptime)
          avqs.append(AVQS)
          pd.append(PD)
        #PS.append
         # showMeas(td,iat,rtt,pr,PS,time,adist_list)
          FB.append(1)
          TB.append(j)
        j=j+1
 
  
def b3ping():
    j=1
    while(j<=n):
        if(3!=j):
          print("From Bus", 3 ," to Bus",j)
         # a=adist()
          #samptime,time,rtt,td,iat,pr,PS=Rhop1(adist,sdistL,sdistLack,time_s,time_e,sampl) 
          sr,acksz,packsz,AT,AVQS,SO,ar,samptime,time,rtt,td,iat,pr,PD=Rhop1(sdistL,sdistLack,time_s,time_e,sampl)          
          SR.append(sr)
          ACKSZ.append(acksz)
          PACKSZ.append(packsz)
          ATm.append(AT) 
          AR.append(ar)
          so.append(SO)
          RTT.append(rtt)
          TD.append(td)
          IAT.append(iat)
          PR.append(pr)
          Time.append(time)
          sampletime.append(samptime)
          avqs.append(AVQS)
          pd.append(PD)
        #PS.append
          #showMeas(td,iat,rtt,pr,PS,time,adist_list)
          FB.append(3)
          TB.append(j)
        j=j+1
def b2ping():
    j=1
    while(j<=n):
        if(2!=j):
          print("From Bus", 2 ," to Bus",j)
          # a=adist()
          #samptime,time,rtt,td,iat,pr,PS=Rhop1(adist,sdistL,sdistLack,time_s,time_e,sampl) 
          sr,acksz,packsz,AT,AVQS,SO,ar,samptime,time,rtt,td,iat,pr,PD=Rhop1(sdistL,sdistLack,time_s,time_e,sampl)          
          SR.append(sr) 
          ACKSZ.append(acksz)
          PACKSZ.append(packsz)
          ATm.append(AT)
          AR.append(ar)
          so.append(SO)
          RTT.append(rtt)
          TD.append(td)
          IAT.append(iat)
          PR.append(pr)
          Time.append(time)
          sampletime.append(samptime)
          avqs.append(AVQS)
          pd.append(PD)
        #PS.append
         # showMeas(td,iat,rtt,pr,PS,time,adist_list)
          FB.append(2)
          TB.append(j)
        j=j+1
def b4ping():
    j=1
    while(j<=n):
        if(4!=j):
          print("From Bus", 4 ," to Bus",j)
          #a=adist()
          #samptime,time,rtt,td,iat,pr,PS=Rhop1(adist,sdistL,sdistLack,time_s,time_e,sampl) 
          sr,acksz,packsz,AT,AVQS,SO,ar,samptime,time,rtt,td,iat,pr,PD=Rhop1(sdistL,sdistLack,time_s,time_e,sampl)          
          SR.append(sr) 
          ACKSZ.append(acksz)
          PACKSZ.append(packsz)
          ATm.append(AT) 
          AR.append(ar)
          so.append(SO)
          RTT.append(rtt)
          TD.append(td)
          IAT.append(iat)
          PR.append(pr)
          Time.append(time)
          sampletime.append(samptime)
          avqs.append(AVQS)
          pd.append(PD)
        #PS.append
         # showMeas(td,iat,rtt,pr,PS,time,adist_list)
          FB.append(4)
          TB.append(j)
        j=j+1
 
def b6ping():
    j=1
    while(j<=n):
        if(6!=j):
          print("From Bus", 6 ," to Bus",j)
          #a=adist()
          #samptime,time,rtt,td,iat,pr,PS=Rhop1(adist,sdistL,sdistLack,time_s,time_e,sampl) 
          sr,acksz,packsz,AT,AVQS,SO,ar,samptime,time,rtt,td,iat,pr,PD=Rhop1(sdistL,sdistLack,time_s,time_e,sampl)          
          SR.append(sr) 
          ACKSZ.append(acksz)
          PACKSZ.append(packsz)
          ATm.append(AT) 
          AR.append(ar)
          so.append(SO)
          RTT.append(rtt)
          TD.append(td)
          IAT.append(iat)
          PR.append(pr)
          Time.append(time)
          sampletime.append(samptime)
          avqs.append(AVQS)
          pd.append(PD)
        #PS.append
          #showMeas(td,iat,rtt,pr,PS,time,adist_list)
          FB.append(6)
          TB.append(j)
        j=j+1
 
def b8ping():
    j=1
    while(j<=n):
        if(8!=j):
          print("From Bus", 8 ," to Bus",j)
          #a=adist()
          #samptime,time,rtt,td,iat,pr,PS=Rhop1(adist,sdistL,sdistLack,time_s,time_e,sampl) 
          sr,acksz,packsz,AT,AVQS,SO,ar,samptime,time,rtt,td,iat,pr,PD=Rhop1(sdistL,sdistLack,time_s,time_e,sampl)          
          SR.append(sr) 
          ACKSZ.append(acksz)
          PACKSZ.append(packsz)
          ATm.append(AT) 
          AR.append(ar)
          so.append(SO)
          RTT.append(rtt)
          TD.append(td)
          IAT.append(iat)
          PR.append(pr)
          Time.append(time)
          sampletime.append(samptime)
          avqs.append(AVQS)
          pd.append(PD)
        #PS.append
         # showMeas(td,iat,rtt,pr,PS,time,adist_list)
          FB.append(8)
          TB.append(j)
        j=j+1
def b10ping():
    j=1
    while(j<=n):
        if(10!=j):
          print("From Bus", 10 ," to Bus",j)
          #a=adist()
          #samptime,time,rtt,td,iat,pr,PS=Rhop1(adist,sdistL,sdistLack,time_s,time_e,sampl) 
          sr,acksz,packsz,AT,AVQS,SO,ar,samptime,time,rtt,td,iat,pr,PD=Rhop1(sdistL,sdistLack,time_s,time_e,sampl)          
          SR.append(sr) 
          ACKSZ.append(acksz)
          PACKSZ.append(packsz)
          ATm.append(AT) 
          AR.append(ar)
          so.append(SO)
          RTT.append(rtt)
          TD.append(td)
          IAT.append(iat)
          PR.append(pr)
          Time.append(time)
          sampletime.append(samptime)
          avqs.append(AVQS)
          pd.append(PD)
        #PS.append
          #showMeas(td,iat,rtt,pr,PS,time,adist_list)
          FB.append(10)
          TB.append(j)
        j=j+1
 
def b12ping():
    j=1
    while(j<=n):
        if(12!=j):
          print("From Bus", 12 ," to Bus",j)
          #a=adist()
          #samptime,time,rtt,td,iat,pr,PS=Rhop1(adist,sdistL,sdistLack,time_s,time_e,sampl) 
          sr,acksz,packsz,AT,AVQS,SO,ar,samptime,time,rtt,td,iat,pr,PD=Rhop1(sdistL,sdistLack,time_s,time_e,sampl)          
          SR.append(sr) 
          ACKSZ.append(acksz)
          PACKSZ.append(packsz)
          ATm.append(AT) 
          AR.append(ar)
          so.append(SO)
          RTT.append(rtt)
          TD.append(td)
          IAT.append(iat)
          PR.append(pr)
          Time.append(time)
          sampletime.append(samptime)
          avqs.append(AVQS)
          pd.append(PD)
        #PS.append
         # showMeas(td,iat,rtt,pr,PS,time,adist_list)
          FB.append(12)
          TB.append(j)
        j=j+1
 
def b5ping():
    j=1
    while(j<=n):
        if(5!=j):
          print("From Bus", 5 ," to Bus",j)
          #a=adist()
          #samptime,time,rtt,td,iat,pr,PS=Rhop1(adist,sdistL,sdistLack,time_s,time_e,sampl) 
          sr,acksz,packsz,AT,AVQS,SO,ar,samptime,time,rtt,td,iat,pr,PD=Rhop1(sdistL,sdistLack,time_s,time_e,sampl)          
          SR.append(sr) 
          ACKSZ.append(acksz)
          PACKSZ.append(packsz)
          ATm.append(AT) 
          AR.append(ar)
          so.append(SO)
          RTT.append(rtt)
          TD.append(td)
          IAT.append(iat)
          PR.append(pr)
          Time.append(time)
          sampletime.append(samptime)
          avqs.append(AVQS)
          pd.append(PD)
        #PS.append
          #showMeas(td,iat,rtt,pr,PS,time,adist_list)
          FB.append(5)
          TB.append(j)
        j=j+1
 
 
def b7ping():
    j=1
    while(j<=n):
        if(7!=j):
          print("From Bus", 7 ," to Bus",j)
          #a=adist()
         # samptime,time,rtt,td,iat,pr,PS=Rhop1(adist,sdistL,sdistLack,time_s,time_e,sampl) 
          sr,acksz,packsz,AT,AVQS,SO,ar,samptime,time,rtt,td,iat,pr,PD=Rhop1(sdistL,sdistLack,time_s,time_e,sampl)          
          SR.append(sr) 
          ACKSZ.append(acksz)
          PACKSZ.append(packsz)
          ATm.append(AT) 
          AR.append(ar)
          so.append(SO)
          RTT.append(rtt)
          TD.append(td)
          IAT.append(iat)
          PR.append(pr)
          Time.append(time)
          sampletime.append(samptime)
          avqs.append(AVQS)
          pd.append(PD)
        #PS.append
          #showMeas(td,iat,rtt,pr,PS,time,adist_list)
          FB.append(7)
          TB.append(j)
        j=j+1
 
def b9ping():
    j=1
    while(j<=n):
        if(9!=j):
          print("From Bus", 9 ," to Bus",j)
          #a=adist()
          #samptime,time,rtt,td,iat,pr,PS=Rhop1(adist,sdistL,sdistLack,time_s,time_e,sampl) 
          sr,acksz,packsz,AT,AVQS,SO,ar,samptime,time,rtt,td,iat,pr,PD=Rhop1(sdistL,sdistLack,time_s,time_e,sampl)          
          SR.append(sr) 
          ACKSZ.append(acksz)
          PACKSZ.append(packsz)
          ATm.append(AT) 
          AR.append(ar)
          so.append(SO)
          RTT.append(rtt)
          TD.append(td)
          IAT.append(iat)
          PR.append(pr)
          Time.append(time)
          sampletime.append(samptime)
          avqs.append(AVQS)
          pd.append(PD)
        #PS.append
          #showMeas(td,iat,rtt,pr,PS,time,adist_list)
          FB.append(9)
          TB.append(j)
        j=j+1
 
def b11ping():
    j=1
    while(j<=n):
        if(11!=j):
          print("From Bus", 11 ," to Bus",j)
          #a=adist()
          #samptime,time,rtt,td,iat,pr,PS=Rhop1(adist,sdistL,sdistLack,time_s,time_e,sampl) 
          sr,acksz,packsz,AT,AVQS,SO,ar,samptime,time,rtt,td,iat,pr,PD=Rhop1(sdistL,sdistLack,time_s,time_e,sampl)          
          SR.append(sr)
          ACKSZ.append(acksz)
          PACKSZ.append(packsz)
          ATm.append(AT) 
          AR.append(ar)
          so.append(SO)
          RTT.append(rtt)
          TD.append(td)
          IAT.append(iat)
          PR.append(pr)
          Time.append(time)
          sampletime.append(samptime)
          avqs.append(AVQS)
          pd.append(PD)
        #PS.append
          #showMeas(td,iat,rtt,pr,PS,time,adist_list)
          FB.append(11)
          TB.append(j)
        j=j+1
 
def b13ping():
    j=1
    while(j<=n):
        if(13!=j):
          print("From Bus", 13 ," to Bus",j)
          #a=adist()
          sr,acksz,packsz,AT,AVQS,SO,ar,samptime,time,rtt,td,iat,pr,PD=Rhop1(sdistL,sdistLack,time_s,time_e,sampl)          
          SR.append(sr)
          ACKSZ.append(acksz)
          PACKSZ.append(packsz)
          ATm.append(AT)
          AR.append(ar)
          so.append(SO)
          RTT.append(rtt)
          TD.append(td)
          IAT.append(iat)
          PR.append(pr)
          Time.append(time)
          sampletime.append(samptime)
          avqs.append(AVQS)
          pd.append(PD)
        #PS.append
          #showMeas(td,iat,rtt,pr,PS,time,adist_list)
          FB.append(13)
          TB.append(j)
        j=j+1
#def evenping():
#    p=2
#   while(p<=n-1):
  #      j=1
   #     while(j<=n):
    #        if(p!=j):
     #         print("From Bus", p ," to Bus",j)
      #        time,rtt,td,iat,pr,PS=Rhop1(adist,sdistL,sdistLack) 
       #       RTT.append(rtt)
        #      TD.append(td)
         #     IAT.append(iat)
          #    PR.append(pr)
#              Time.append(time)
#           #PS.append
  #            showMeas(td,iat,rtt,pr,PS,time)
   #           FB.append(p)
    #          TB.append(j)
     #       j=j+1
      #  p=p+2
 
def Rhop1(n,nack,time_s,time_e,sampl):
    k=1
    pd=0
    env = simpy.Environment()  # Create the SimPy environment
    # Create the packet generators and sink
    #a=functools.partial(random.choice(adist_list))
    a=random.expovariate(7)
    def arr():
         return a    
    s=random.expovariate(0.001)
    def psz():
         return s 
    sa=random.expovariate(0.064)
    def sack():
         return sa 

    AR= (float(s))/(float(a))
    ps = PacketSink(env, debug=False, rec_arrivals=True, absolute_arrivals=False)
    pg = PacketGenerator(env, "Greg", arr, psz)
    switch_port = SwitchPort(env, port_rate_norm, qlimit_norm)
    # Using a PortMonitor to track queue sizes over time
    pm = PortMonitor(env, switch_port, samp_dist)
    # Wire packet generators, switch ports, and sinks together
    pg.out = switch_port
    switch_port.out = ps 
    # Run it
    env.run(until=15)
    pg2 = PacketGenerator(env, "", arr, sack)
    ps2 = PacketSink(env, debug=False, rec_arrivals=True, absolute_arrivals=False)
    pg2.out=switch_port
    switch_port.out=ps2
    env.run(until=16)
    #RTT=max(ps.waits)+max(ps2.waits)+max(ps.arrivals)
    RTT=sum(ps.waits)/len(ps.waits)+sum(ps2.waits)/len(ps2.waits)+sum(ps.arrivals)/len(ps.arrivals) 
    TD=sum(ps.waits)/len(ps.waits)
    IAT=a
    AT=sum(ps.arrivals)/len(ps.arrivals)
    pasz=s
    acksz=sa
    for i in range (len(pm.sizes)):
        if pm.sizes[i] != 0:
            k=k+1
    so=sum(pm.sizes)/len(pm.sizes)
    if so==0:
        sr=AR
    if so!=0:
        sr=AR/so
    avqs=sum(pm.sizes)/k
    pd=pg.packets_sent-ps.packets_rec
    #if(time_e-time_s>2.1):
        #time_s=time_e
        #sampl=sampl+1
    time_now = datetime.now()
    timed=time.time()
    Time =time_now.strftime("%H:%M:%S:%f") 
    print("Arival rate and System Occupancy : ",AR,so,avqs,k,pm.sizes,pd) 

    #return(iatd,AR,timed,Time,RTT,format(max(ps.waits)),format(max(ps.arrivals)), format(ps.packets_rec), format(pg.packets_sent))
    return(sr,acksz,pasz,AT,avqs,so,AR,timed,Time,RTT,TD,IAT, ps.packets_rec, pd)
####   NOT USED  ####
#def busping(n):
#   for i in range (n):
#        print("From Bus {} to Bus {}", format(i), format(i+1))
#        if i==1 & n==2:
#            RTT,TD,IAT,PR,PS=Rhop1(adist,sdist) 
#        else:
#            P,RTT,TD,IAT,PR,PS=Shop1(adist,sdist) 
    """           
def showMeas(TD,IAT,RTT,PR,PS,Time,ad):
    print("\nTransmission Delay:",TD)
            #print("G_Transmission Delay: {}".format(max(ps2.waits)))
    print("Inter-Arrival Time:", IAT)
           # print("G_Inter-Arrival Time: {}".format(max(ps2.arrivals)))
    print("Round Trip Time (RTT): ",RTT)
    print("Packet received: {}, Packet sent {}".format(PR,PS)) 
    print("Time : ",Time)  
    print("Arival rate : ",ad)  
    """       

 
#####################################################################################
 
#####################################################################################
 
# Variables for switch function in simulation
port_rate_norm = 100000.0
port_rate_mal = 30.0
qlimit_norm = 1000000
qlimit_mal = 100000
n=14
 
#####################################################################################
 
#####################################################################################
 
#Execute the simulation
if __name__ == '__main__':
    FB=[]
    TB=[]
    RTT=[]
    TD=[]
    PR=[]
    IAT=[]
    Time=[]
    sample=[]  
    sampletime=[]
    start=time.time()
    end=time.time()
    sampl=1
    AR=[]
    SR=[]
    iatd=[]
    so=[]
    avqs=[]
    pd=[]
    ACKSZ=[]
    ATm=[]
    PACKSZ=[]
    #p=2
    #for j in range(2):
    #for i in range(n-1):
    #print("START")
    #print("start time is", time_s)
    #time.sleep(5)
   # time_e=time.time()
    #print("End time is :", time_e)
    while(end<start+120):
        t1=threading.Thread(target=b1ping)
        t1.start()
        t8=threading.Thread(target=b8ping)
        t8.start()
        t3=threading.Thread(target=b3ping)
        t3.start()
        t10=threading.Thread(target=b10ping)
        t10.start()
        t5=threading.Thread(target=b5ping())
        t5.start()
        t12=threading.Thread(target=b12ping)
        t12.start()
        t7=threading.Thread(target=b7ping())
        t7.start()
        t9=threading.Thread(target=b9ping)
        t9.start()     
   # to=threading.Thread(target=evenping())
   # to.start()
        t2=threading.Thread(target=b2ping)
        t2.start()
        t11=threading.Thread(target=b11ping)
        t11.start()
        t4=threading.Thread(target=b4ping())
        t4.start()
        t13=threading.Thread(target=b13ping)
        t13.start()
        t6=threading.Thread(target=b6ping)       
        t6.start()  
        #t6.join() 
        end=time.time()
 
    sampling(sampletime,sample)                
    Measurements(FB,TB,IAT,TD,PR,RTT,avqs,so,AR,pd,Time,sample)
   # iatdistributions(iatd)
   # ARdistributions(AR)
Measlist=[FB,TB,IAT,TD,PR,RTT,Time,sample]
Meas=['From Bus','To Bus', 'Inter Arrival Time','Transmission Delay','Packet Count', 'Round Trip Time','Time','Sample #']      
#df = pd.DataFrame (Measlist,Meas)
#print (df)   