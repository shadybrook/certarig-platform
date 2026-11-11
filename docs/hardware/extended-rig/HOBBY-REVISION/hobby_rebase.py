from pathlib import Path
import csv,gzip,json,math,hashlib,itertools
import numpy as np
OUT=Path('outputs/Original_Hobby_Bench');OUT.mkdir(parents=True,exist_ok=True)
rows=[('Pump',600,500,900,'Small12V low-head centrifugal; listing scale only; startup/head curve needed'),('NC direct-acting valve',1000,800,1500,'12V zero-differential; local quote required, no motorized industrial actuator'),('Pressure sensor',3000,2600,3500,'0-0.5bar class range; exact transfer/accuracy must be confirmed; PR19C050K conflicting sheet remains on hold'),('Flow sensor',300,250,400,'YF-S302 class; calibrate actual low-flow pulse curve'),('Temperature probes',300,300,500,'Two DS18B20-class powered probes'),('Current measurement',400,300,600,'INA219-class module(s); input/shunt/clamp review required'),('Supply and converters',1000,1000,1500,'Enclosed12V supply, field buck and24V loop boost if transmitter needs it; Pi PSU reused'),('Actuator protection and controls',1200,900,1600,'Drivers, suppression, fuses, manually reset hardware cutoff, STOP/RESET; existing E-stop only after acceptance'),('Basic field isolation/interfaces',1000,900,1800,'I2C isolation + field temperature bridge and digital optoisolation allowance; exact board quotes pending'),('Level/leak/thermal switches',300,300,700,'Hobby switches, independent cutoff where appropriate; no certified safety function claim'),('Box and terminals',500,500,1000,'Small box, terminals, wire; reuse acceptable stock'),('Plumbing and mounting',1500,1800,3200,'Includes hose, barbs, tees, clamps, permanently open bypass, reservoir and tray'),('Simple references',300,400,800,'Water-column/volume/temperature comparisons, borrowed references where accepted'),('Development storage',600,500,800,'NewmicroSD; preserve original Phase3 card'),('Pressure-protection allowance',1500,None,None,'UNPRICED: compatible relief/arrestor solution or a validated lower-energy envelope. Generic domestic arrestor pair is not assumed compatible.'),('Delivery and spares',1000,700,1500,'Planning allowance')]
fields=['item','target_INR','low_INR','high_INR','basis']
with (OUT/'Hobby_cost_breakdown.csv').open('w',newline='') as f:w=csv.writer(f);w.writerow(fields);w.writerows(rows)
target=sum(r[1] for r in rows);lo=sum(r[2] or 0 for r in rows);hi=sum(r[3] or 0 for r in rows)
# Original recirculating topology: pump -> pressure tee -> permanent bypass
# plus restricted valve branch -> open reservoir. A stiff0.30bar source bounds
# pump/manifold pressure; bypass is not counted as a fast wave absorber.
res=[]
for wave,closure,dt in [(200,.02,1e-5),(400,.02,1e-5),(1000,.02,1e-5),(1000,.005,1e-5),(1000,.005,5e-6),(1000,.001,2e-6)]:
 rho=1000;area=math.pi*.012**2/4;length=.5;L=rho*length/area;C=area*length/(rho*wave**2);ps=30000.;q0=.5/60000;R=.1*ps/q0**2;kv=q0/math.sqrt(.9*ps);y=np.array([q0,.9*ps]);trace=[]
 def f(t,y):
  q,p=y;s=max(.0001,1-max(0,t-.02)/closure)
  return np.array([(ps-p-R*q*abs(q))/L,(q-kv*s*math.copysign(math.sqrt(abs(p)),p))/C])
 for n in range(round((.04+closure)/dt)+1):
  t=n*dt;trace.append((t,*map(float,y)));a=f(t,y);b=f(t+dt/2,y+a*dt/2);c=f(t+dt/2,y+b*dt/2);d=f(t+dt,y+c*dt);y+=dt*(a+2*b+2*c+d)/6
 a=np.array(trace);name=f'c{wave}_close{closure}_dt{dt}'
 with gzip.open(OUT/(name+'.csv.gz'),'wt',newline='') as f:w=csv.writer(f);w.writerow(['time_s','branch_flow_m3_s','pressure_Pa']);w.writerows(trace)
 res.append(dict(name=name,parameters=dict(source_bar=.3,flow_L_min=.5,hose_length_m=.5,hose_ID_m=.012,wave_m_s=wave,closing_s=closure,dt_s=dt),peak_bar=float(max(a[:,2])/1e5),min_bar=float(min(a[:,2])/1e5),within_0_5bar_measurement=bool(max(a[:,2])<50000),below_1bar_proof=bool(max(a[:,2])<100000),single_phase=bool(min(a[:,2])> -95000)))
result=dict(budget_target_INR=target,known_allowance_range_excluding_pressure_protection_INR=[lo,hi],pressure_protection_quote=None,hydraulic_cases=res,qualification='Conditional reduced-model experiments only; exact hardware is not selected or physically verified. No R3 header-tank or industrial-panel results are transferred to this proposal.')
(OUT/'Hobby_review_results.json').write_text(json.dumps(result,indent=2)+'\n')
# Replay extrema from each saved raw trace.
for r in res:
 with gzip.open(OUT/(r['name']+'.csv.gz'),'rt') as f:a=np.loadtxt(f,delimiter=',',skiprows=1)
 assert np.isfinite(a).all() and math.isclose(max(a[:,2])/1e5,r['peak_bar'],abs_tol=1e-10)
 assert a[-1,0]>=.04+r['parameters']['closing_s']-r['parameters']['dt_s']
(OUT/'verification.json').write_text(json.dumps(dict(saved_trace_extrema_replayed=len(res),model_only=True),indent=2)+'\n')
print(json.dumps(result,indent=2))
