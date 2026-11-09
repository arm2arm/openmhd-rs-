use mhd_core::{IdealGas,Primitive,FaceCompletion,riemann_with_completion,cross};
fn main(){
 let eos=IdealGas::new(5./3.).unwrap(); let n=[1.,0.,0.];
 let mut l=Primitive{density:1.,pressure:1.,velocity:[0.,0.2,0.1],magnetic:[0.5,0.3,0.1]};
 let mut r=Primitive{density:1.,pressure:1.,velocity:[0.,-0.2,0.05],magnetic:[0.5,-0.4,0.2]};
 let cf=eos.fast_speed(l,n).max(eos.fast_speed(r,n));
 for dv in [-1e-12, -1e-15, 0., 1e-15, 1e-12] {
  l.velocity[0]=cf+dv;r.velocity[0]=cf+dv;
  let f=riemann_with_completion(eos,l,r,n,[0.;3],FaceCompletion::HllAverage).unwrap();
  let ub=cross([cf,0.,0.],f.magnetic);
  let s:[f64;3]=std::array::from_fn(|k|f.electromotive[k]-ub[k]);
  println!("dv={dv:.3e} method={:?}, source={s:?}, B={:?}, flux={:?}",f.method,f.magnetic,f.fluid);
 }
}
