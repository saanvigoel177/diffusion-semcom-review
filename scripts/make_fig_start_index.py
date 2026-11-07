"""Start index m versus SNR for linear-beta and cosine schedules (T=1000).
Reproduces Table 5 and draws Figure 4 (Section 2.3)."""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
matplotlib.rcParams.update({"pdf.fonttype":42,"ps.fonttype":42,"font.family":"serif",
    "font.serif":["Palatino Linotype","Palatino","TeX Gyre Pagella","DejaVu Serif"],"font.size":9,
    "mathtext.fontset":"cm"})
T=1000
beta=np.linspace(1e-4,0.02,T)
abar_lin=np.cumprod(1-beta)
s=0.008
t=np.arange(0,T+1)/T
f=np.cos((t+s)/(1+s)*np.pi/2)**2
abar_cos=(f/f[0])[1:]            # index 1..T
def start_index(abar_target,abar):
    # smallest index m (1-based) whose abar_m <= target, i.e. noise at least as large
    hit=np.nonzero(abar<=abar_target)[0]
    if hit.size==0: raise ValueError("target below the end of the schedule")
    return int(hit[0])+1
snr_db=np.array([0,5,10,15,20,30])
tab=[]
for d in snr_db:
    snr=10**(d/10); a=snr/(1+snr)
    tab.append((d,a,start_index(a,abar_lin),start_index(a,abar_cos)))
for r in tab: print("%2d dB  abar=%.3f  linear=%3d  cosine=%3d"%r)
TAB_LIN=[260,162,94,52,28,7]; TAB_COS=[497,321,189,106,57,14]  # values printed in Table 5
if [r[2] for r in tab]!=TAB_LIN or [r[3] for r in tab]!=TAB_COS:
    raise SystemExit("Computed start indices differ from Table 5")
print("Table 5 reproduced")
grid=np.linspace(0,30,121)
a=(10**(grid/10))/(1+10**(grid/10))
m_lin=[start_index(x,abar_lin) for x in a]; m_cos=[start_index(x,abar_cos) for x in a]
fig,ax=plt.subplots(figsize=(3.4,2.5),dpi=300)
c1,c2="#1b4f9c","#c4570a"
ax.plot(grid,m_cos,color=c2,lw=1.6,ls="--",label="cosine")
ax.plot(grid,m_lin,color=c1,lw=1.6,ls="-",label="linear $\\beta$")
ax.plot(snr_db,[r[3] for r in tab],"s",ms=4.5,mfc="white",mec=c2,mew=1.2)
ax.plot(snr_db,[r[2] for r in tab],"o",ms=4.5,mfc="white",mec=c1,mew=1.2)
ax.set_yscale("log"); ax.set_xlim(0,30); ax.set_ylim(5,700)
ax.set_xlabel("Channel SNR (dB)"); ax.set_ylabel("Start index $m$ ($T=1000$)")
ax.set_yticks([10,100,500]); ax.set_yticklabels(["10","100","500"])
ax.grid(True,which="major",lw=0.4,color="#d0d0d0"); 
for sp in ("top","right"): ax.spines[sp].set_visible(False)
ax.legend(frameon=False,loc="upper right",fontsize=8)
fig.tight_layout(pad=0.4); fig.savefig("fig_start_index.pdf")
