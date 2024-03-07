"""
Solves the incompressible Navier-Stokes equations in conjunction with
an advection equation in a closed box.

Momentum:           ∂u/∂t + (u ⋅ ∇) u = − 1/ρ ∇p + ν ∇²u + f

Incompressibility:  ∇ ⋅ u = 0

Advection:          ∂s/∂t + (u ⋅ ∇) s = α ∇²s + i

u:  Velocity (2d vector)
p:  Pressure
f:  Forcing (here due to Buoyancy)
ν:  Kinematic Viscosity
ρ:  Density (here =1.0)
t:  Time
∇:  Nabla operator (defining nonlinear convection, gradient and divergence)
∇²: Laplace Operator
s:  Concentration of a species (here hot smoke)
α:  Diffusivity of the embedded species
i:  Inflow of hot smoke into the domain.

----------

Scenario


    +----------------------------------------------+
    |                                              |
    |                                              |
    |                                              |
    |                                              |
    |                                              |
    |                                              |
    |                                              |
    |                                              |
    |                                              |
    |                                              |
    |                                              |
    |                                              |
    |           _                                  |
    |          / \                                 |
    |         |   |                                |
    |          \_/                                 |
    |                                              |
    +----------------------------------------------+

-> Domain is square and closed-off (wall BC everywhere)
-> Initially, the fluid is at rest
-> Initially, the concentration of smoke is zero everywhere
-> There is a continuous inflow of hot smoke in a small circular
   patch in the bottom left of the domain
-> The hot smoke exerts a force on the fluid due to Buyancy
-> This makes the fluid flow upwards and create a plume pattern

-------

Solution strategy:

Initialize the fluid velocity vectors to zero on a Staggered Grid.

Initialize the smoke density to zero on a Centered Grid.

1. Advect the smoke density by a MacCormack step

2. Add the inflow of hot smoke to the smoke density field

3. Compute the Buoyancy force by re-sampling the centered
   smoke densities on the staggered velocities

4. Convect the fluid by means of a semi-lagrangian self-avection
   step 

5. Add the Buoyancy force to the fluid

6. Make the fluid incompressible

7. Repeat


Note, that we did not apply any diffusion on both the fluid and
the smoke concentration. This is done for simplicity, the involved
convection/advection procedures introduce considerable numerical
diffusion which stabilize the simulation.
"""

from phi.jax import flow
import matplotlib.pyplot as plt
from tqdm import tqdm
from phi.flow import *

N_TIME_STEPS = 150

def main():



    @flow.math.jit_compile
    def step_inflow(velocity_prev, smoke_prev, inflow, dt=1.0):
        smoke_next = flow.advect.mac_cormack(smoke_prev, velocity_prev, dt) + inflow[0] + inflow[1]
        buoyancy_force = smoke_next * (0.0, 0.1) @ velocity
        velocity_tent = flow.advect.semi_lagrangian(velocity_prev, velocity_prev, dt) + buoyancy_force * dt
        velocity_next, pressure = flow.fluid.make_incompressible(velocity_tent)
        return velocity_next, smoke_next
    
    @flow.math.jit_compile
    def step_no_inflow(velocity_prev, smoke_prev, inflow, dt=1.0):
        smoke_next = flow.advect.mac_cormack(smoke_prev, velocity_prev, dt)
        buoyancy_force = smoke_next * (0.0, 0.1) @ velocity
        velocity_tent = flow.advect.semi_lagrangian(velocity_prev, velocity_prev, dt) + buoyancy_force * dt
        velocity_next, pressure = flow.fluid.make_incompressible(velocity_tent)
        return velocity_next, smoke_next

    velocity = flow.StaggeredGrid(
        values=(0.0, 0.0),
        extrapolation=0.0,
        x=64,
        y=64,
        bounds=flow.Box(x=100, y=300),
    )
    smoke = flow.CenteredGrid(
        values=0.0,
        extrapolation=flow.extrapolation.BOUNDARY,
        x=200,
        y=200,
        bounds=flow.Box(x=100, y=300),
    )
    
    # inflow = 0.2 * flow.CenteredGrid(
    #     values=flow.SoftGeometryMask(
    #         flow.Sphere(
    #             x=60,
    #             y=9.5,
    #             radius=5,
    #         ),
    #     ),
    #     extrapolation=0.0,
    #     bounds=smoke.bounds,
    #     resolution=smoke.resolution,
    # )

    inflow = [
        2.2 * flow.CenteredGrid(
        values=flow.SoftGeometryMask(flow.Sphere(x=60,y=9.5,radius=5,),),
        extrapolation=0.0,
        bounds=smoke.bounds,
        resolution=smoke.resolution),
        .8 * flow.CenteredGrid(
        values=flow.SoftGeometryMask(flow.Sphere(x=10,y=50,radius=5,),),
        extrapolation=0.0,
        bounds=smoke.bounds,
        resolution=smoke.resolution)
    ]

    
    plt.style.use("dark_background")
    
    trajectory = [smoke]
    for i in tqdm(range(N_TIME_STEPS)):
        if i < 50:
            velocity, smoke = step_inflow(velocity, smoke, inflow)
        else:
            velocity, smoke = step_no_inflow(velocity, smoke, inflow)
        trajectory.append(smoke)
        smoke_values_extracted = smoke.values.numpy("y,x")
        plt.imshow(smoke_values_extracted, origin="lower")
        plt.draw()
        plt.pause(0.01)
        plt.clf()
        
    trajectory = field.stack(trajectory, batch('time'))
    vis.plot(trajectory, animate='time')


if __name__ == "__main__":
    main()