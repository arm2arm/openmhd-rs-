use mhd_vector_pot::general::{Config, Initial, Motion, Simulation};
use moving_mesh::Mesh;
use std::f64::consts::TAU;
fn initial(x: [f64;2], boost: [f64;3])->Initial {
 let (x,y)=(TAU*x[0]/1.3,TAU*x[1]/0.7);
 Initial {density:1.0+0.01*x.sin(),pressure:1.0+0.01*y.cos(),velocity:[0.2+0.05*y.sin()+boost[0],-0.1+0.03*x.cos()+boost[1],0.04*(x+y).sin()+boost[2]],potential:[0.001*y.sin(),0.001*x.cos(),0.001*x.sin()*y.sin()],phi:0.0001*(x+y).cos()}
}
fn main(){
 for jitter in [0.0,0.15] { for fluid in [false,true] { let limited=true;
  let mesh=Mesh::lattice(6,8,[1.3,0.7],jitter).unwrap();
  let boost=[2.0,-1.0,0.8];
  let w:Vec<_>=mesh.generators.iter().map(|p|[0.1*(TAU*p[1]/0.7).sin(),0.1*(TAU*p[0]/1.3).cos()]).collect();
  let wb=w.iter().map(|v|[v[0]+boost[0],v[1]+boost[1]]).collect();
  let mut a=Simulation::new(mesh.clone(),Config{motion:if fluid {Motion::Fluid} else {Motion::Prescribed(w)},limited,mean_magnetic:[0.3,0.2,0.1],max_dt:0.0005,..Config::default()},|x|initial(x,[0.0;3])).unwrap();
  let mut b=Simulation::new(mesh,Config{motion:if fluid {Motion::Fluid} else {Motion::Prescribed(wb)},limited,mean_magnetic:[0.3,0.2,0.1],max_dt:0.0005,..Config::default()},|x|initial(x,boost)).unwrap();
  a.advance_to(0.01).unwrap();b.advance_to(0.01).unwrap();
  let mut err=0.0_f64; let mut per=[0.0_f64;4];
  for (qa,qb) in a.primitives().unwrap().iter().zip(b.primitives().unwrap()) {
   per[0]=per[0].max((qa.density-qb.density).abs());per[1]=per[1].max((qa.pressure-qb.pressure).abs()); err=err.max(per[0]).max(per[1]);
   for k in 0..3 {per[2]=per[2].max((qa.velocity[k]-qb.velocity[k]+boost[k]).abs());per[3]=per[3].max((qa.magnetic[k]-qb.magnetic[k]).abs());err=err.max(per[2]).max(per[3]);}
  }

  assert_eq!(a.counters().auxiliary_roots,b.counters().auxiliary_roots);
  println!("jitter={jitter} rho_p_v_B={per:?} fluid={fluid} limited={limited} max_physical_error={err:.6e} steps={}/{} rejection_counts={}/{}/{} vs {}/{}/{}",a.counters().steps,b.counters().steps,a.counters().rejected_state,a.counters().rejected_geometry,a.counters().rejected_cfl,b.counters().rejected_state,b.counters().rejected_geometry,b.counters().rejected_cfl);
 }}
}
