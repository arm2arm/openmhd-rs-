use mhd_core::{IdealGas,Primitive,FaceCompletion,riemann_with_completion,cross};
fn main(){
 let eos=IdealGas::new(5./3.).unwrap(); let n=[1.,0.,0.];
 let mut l=Primitive{density:1.,pressure:1.,velocity:[0.,0.2,0.1],magnetic:[0.5,0.3,0.1]};
 let mut r=Primitive{density:1.,pressure:1.,velocity:[0.,-0.2,0.05],magnetic:[0.5,-0.4,0.2]};
 let cf=eos.fast_speed(l,n).max(eos.fast_speed(r,n)); l.velocity[0]=cf;r.velocity[0]=cf;
 for bx in [0.,0.1,0.3,1.,2.,3.,4.,10.,100.,-2.,-4.] {
  let boost=[bx,-1.,0.8];let mut lb=l;let mut rb=r;
  for k in 0..3 {lb.velocity[k]+=boost[k]; rb.velocity[k]+=boost[k];}
  let f=riemann_with_completion(eos,lb,rb,n,boost,FaceCompletion::HllAverage).unwrap();
  let ub=cross([cf+bx,-1.,0.8],f.magnetic);
  let s:[f64;3]=std::array::from_fn(|k|f.electromotive[k]-ub[k]);
  println!("boost={boost:?} dv={:.3e} method={:?} source={s:?}",(cf+bx)-bx-cf,f.method);
 }
}
