use mhd_core::{IdealGas,Primitive,FaceCompletion,riemann,riemann_with_completion,cross};
fn main(){
 let eos=IdealGas::new(5./3.).unwrap(); let mut seed=0x123456789abcdef_u64;
 let mut rnd=|| {seed^=seed<<13;seed^=seed>>7;seed^=seed<<17;(seed>>11) as f64/(1_u64<<53) as f64};
 let mut worst_rev=0_f64;let mut worst_boost=0_f64;let mut valid=0;let mut rejected=0;
 for _ in 0..10000 {
  let mut raw=[0.;24];for v in &mut raw {*v=rnd();}
  let q=|k:usize| Primitive {density:0.1+10.*raw[k],pressure:0.1+3.*raw[k+1],velocity:std::array::from_fn(|i|6.*raw[k+2+i]-3.),magnetic:std::array::from_fn(|i|4.*raw[k+5+i]-2.)};
  let l=q(0); let r=q(8);
  let mut n=[2.*raw[16]-1.,2.*raw[17]-1.,2.*raw[18]-1.];let len=n[0].hypot(n[1]).hypot(n[2]);for v in &mut n {*v/=len;}
  let w=[raw[19]-0.5,raw[20]-0.5,raw[21]-0.5];let aux=[raw[21]-0.5,raw[22]-0.5,raw[23]-0.5];
  let solve=|l,r,n,w|riemann_with_completion(eos,l,r,n,w,FaceCompletion::SignalWeighted);
  let Ok(f)=solve(l,r,n,w) else {rejected+=1;continue};
  let old=riemann(eos,l,r,n,w).unwrap();assert_eq!(old.fluid,f.fluid);assert_eq!(old.induction,f.induction);
  let rev=solve(r,l,n.map(|v|-v),w).unwrap();
  let b=[2.,-1.,0.8];let shift=|mut q:Primitive| {for k in 0..3{q.velocity[k]+=b[k];}q};
  let boosted=solve(shift(l),shift(r),n,std::array::from_fn(|k|w[k]+b[k])).unwrap();
  let ua=cross(aux,f.magnetic);let ur=cross(aux,rev.magnetic);let ub=cross(std::array::from_fn(|k|aux[k]+b[k]),boosted.magnetic);
  for k in 0..3 {worst_rev=worst_rev.max((f.electromotive[k]-ua[k]-rev.electromotive[k]+ur[k]).abs());worst_boost=worst_boost.max((f.electromotive[k]-ua[k]-boosted.electromotive[k]+ub[k]).abs());}
  valid+=1;
 }
 println!("valid={valid} rejected={rejected} max_source_reversal={worst_rev:.6e} max_source_boost={worst_boost:.6e}");
 assert!(worst_rev<1e-11 && worst_boost<1e-11);
}
