#ifndef TESTCELLSORTING_HPP_
#define TESTCELLSORTING_HPP_

#include <cxxtest/TestSuite.h>

// Must be included before other cell_based headers
#include "CellBasedSimulationArchiver.hpp"

#include "AbstractCellBasedWithTimingsTestSuite.hpp"
#include "CellLabel.hpp"
#include "SmartPointers.hpp"
#include "CellsGenerator.hpp"
#include "UniformG1GenerationalCellCycleModel.hpp"
#include "DifferentiatedCellProliferativeType.hpp"

#include "HeterotypicBoundaryLengthWriter.hpp"

#include "OffLatticeSimulation.hpp"
#include "VertexBasedCellPopulation.hpp"
#include "HoneycombVertexMeshGenerator.hpp"
#include "NagaiHondaDifferentialAdhesionForce.hpp"
#include "RandomMotionForce.hpp"

#include "NodesOnlyMesh.hpp"
#include "NodeBasedCellPopulation.hpp"

#include "MeshBasedCellPopulationWithGhostNodes.hpp"
#include "HoneycombMeshGenerator.hpp"
#include "DifferentialAdhesionGeneralisedLinearSpringForce.hpp"
#include "CellPopulationAdjacencyMatrixWriter.hpp"

#include "CellLabelWriter.hpp"
#include "CellMutationStatesWriter.hpp"

#include "PetscSetupAndFinalize.hpp"

static const double M_TIME_TO_STEADY_STATE = 0.0; //10
static const double M_TIME_FOR_SIMULATION = 100.0; //100
static const double M_NUM_CELLS_ACROSS = 20; //20 // this ^2 cells
static const double M_CELL_FLUCTUATION = 1e-2;

class TestCellSorting : public AbstractCellBasedWithTimingsTestSuite
{
private:

    /*
     * This is a helper method to randomly label cells add is used in all simulations.
     */ 

    void RandomlyLabelCells(std::list<CellPtr>& rCells, boost::shared_ptr<AbstractCellProperty> pLabel, double labelledRatio)
    {
        for (std::list<CellPtr>::iterator cell_iter = rCells.begin();
             cell_iter != rCells.end();
             ++cell_iter)
        {
            if (RandomNumberGenerator::Instance()->ranf() < labelledRatio)
            {
               (*cell_iter)->AddCellProperty(pLabel);
            }
        }
    }

    /*
     * This is a helper method to label cells in a block pattern, so that the labelled
     * cells (A) occupy the top half of the domain, sitting on top of the unlabelled
     * cells (B) in the bottom half. The split is based on the cell's row index.
     */
    void BlockLabelCells(AbstractCellPopulation<2>& rCellPopulation, boost::shared_ptr<AbstractCellProperty> pLabel, unsigned numCellsAcross)
    {
        for (AbstractCellPopulation<2>::Iterator cell_iter = rCellPopulation.Begin();
             cell_iter != rCellPopulation.End();
             ++cell_iter)
        {
            unsigned location_index = rCellPopulation.GetLocationIndexUsingCell(*cell_iter);
            unsigned row = location_index / numCellsAcross;
            if (row >= numCellsAcross/2)
            {
                cell_iter->AddCellProperty(pLabel);
            }
        }
    }

public:

    /*
     * == VM ==
     *
     * Simulate a population of cells exhibiting cell sorting using the
     * Cell Vertex model.
     */
    void TestVertexMonolayerCellSorting()
    {
        /*
         * Three choices of differential-adhesion parameters give three qualitatively
         * different behaviours: Sorting, Mixing and Engulfment. The entries below are
         * indexed by regime.
         *
         * For the Nagai-Honda adhesion energy parameters a higher value corresponds to
         * a higher interfacial energy, i.e. a less favourable (weaker) contact.
         */
        std::string adhesion_regimes[3] = {"Sorting", "Engulfment", "Mixing"};

        // double cell_cell_adhesion[3]         = {1.0,  1.0,  2.0};   // unlabelled-unlabelled (gamma_AA)
        // double labelled_labelled_adhesion[3] = {1.0,  1.0,  1.0};   // labelled-labelled     (gamma_BB)
        // double labelled_cell_adhesion[3]     = {2.0,  0.5,  1.5};   // heterotypic           (gamma_AB)
        // double cell_boundary_adhesion[3]     = {10.0, 10.0, 10.0};  // unlabelled-medium
        // double labelled_boundary_adhesion[3] = {20.0, 10.0, 14.0};  // labelled-medium

        // double cell_cell_adhesion[3]         = {1.0,  2.0,  1.0};   // unlabelled-unlabelled (gamma_AA)
        // double labelled_labelled_adhesion[3] = {1.0,  2.0,  1.0};   // labelled-labelled     (gamma_BB)
        // double labelled_cell_adhesion[3]     = {2.0,  1.0,  1.0};   // heterotypic           (gamma_AB)
        // double cell_boundary_adhesion[3]     = {2.0,  1.0, 2.0};  // unlabelled-medium
        // double labelled_boundary_adhesion[3] = {2.0,  1.0, 4.0};  // labelled-medium

        double cell_cell_adhesion[3]         = {1.0,  2.0,  2.0};   // unlabelled-unlabelled (gamma_AA)
        double labelled_labelled_adhesion[3] = {1.0,  1.0,  2.0};   // labelled-labelled     (gamma_BB)
        double labelled_cell_adhesion[3]     = {5.0,  2.0,  1.0};   // heterotypic           (gamma_AB)
        double cell_boundary_adhesion[3]     = {5.0, 20.0, 2.0};  // unlabelled-medium
        double labelled_boundary_adhesion[3] = {5.0, 10.0, 2.0};  // labelled-medium


        // Number of cells across (this^2 cells). Stored as an array so the sweep is easy to extend.
        unsigned num_cells_across_values[1] = {(unsigned) M_NUM_CELLS_ACROSS};

        for (unsigned regime_index = 0; regime_index < 1; regime_index++)
        {
            std::string regime = adhesion_regimes[regime_index];

            // Use a block initial condition for the Engulfment example, and a random
            // initial condition for the Sorting and Mixing examples.
            std::string pattern = (regime.compare("Engulfment")==0) ? "Block" : "Random";

            {

                for (unsigned num_cells_index = 0; num_cells_index < 1; num_cells_index++)
                {
                    unsigned num_cells_across = num_cells_across_values[num_cells_index];

                    // Reseed the random number generator so the initial conditions are reproducible
                    RandomNumberGenerator* p_gen = RandomNumberGenerator::Instance();
                    p_gen->Reseed(100);

                    // Create a simple 2D MutableVertexMesh
                    HoneycombVertexMeshGenerator generator(num_cells_across, num_cells_across);
                    boost::shared_ptr<MutableVertexMesh<2,2> > p_mesh = generator.GetMesh();
                    p_mesh->SetCellRearrangementThreshold(0.1);

                    // Slows things down but can use a larger timestep and diffusion forces
                    //p_mesh->SetCheckForInternalIntersections(true);

                    // Set up cells, one for each VertexElement
                    std::vector<CellPtr> cells;
                    boost::shared_ptr<AbstractCellProperty> p_cell_type(CellPropertyRegistry::Instance()->Get<DifferentiatedCellProliferativeType>());
                    CellsGenerator<UniformG1GenerationalCellCycleModel, 2> cells_generator;
                    cells_generator.GenerateBasicRandom(cells, p_mesh->GetNumElements(), p_cell_type);

                    for (unsigned i=0; i<cells.size(); i++)
                    {
                        // Set a target area rather than setting a growth modifier. (the modifiers don't work correctly as making very long G1 phases)
                        cells[i]->GetCellData()->SetItem("target area", 1.0);
                    }

                    // Create cell population
                    VertexBasedCellPopulation<2> cell_population(*p_mesh, cells);

                    // Set population to output all data to results files
                    cell_population.AddCellWriter<CellLabelWriter>();
                    cell_population.AddCellWriter<CellMutationStatesWriter>();
                    cell_population.AddPopulationWriter<HeterotypicBoundaryLengthWriter>();
                    cell_population.AddPopulationWriter<CellPopulationAdjacencyMatrixWriter>();

                    // Set up cell-based simulation and output directory (one per combination)
                    OffLatticeSimulation<2> simulator(cell_population);

                    std::stringstream output_directory;
                    output_directory << "CellSorting/Vertex/" << regime << "/" << pattern
                                     << "/CellsAcross_" << num_cells_across;
                    simulator.SetOutputDirectory(output_directory.str());

                    // Set time step for simulation
                    simulator.SetDt(1.0/200.0);
                    simulator.SetSamplingTimestepMultiple(200);

                    // Set up force law using the parameters for the current adhesion regime
                    MAKE_PTR(NagaiHondaDifferentialAdhesionForce<2>, p_force);
                    p_force->SetNagaiHondaDeformationEnergyParameter(50.0);
                    p_force->SetNagaiHondaMembraneSurfaceEnergyParameter(1.0);
                    p_force->SetNagaiHondaCellCellAdhesionEnergyParameter(cell_cell_adhesion[regime_index]);
                    p_force->SetNagaiHondaLabelledCellCellAdhesionEnergyParameter(labelled_cell_adhesion[regime_index]);
                    p_force->SetNagaiHondaLabelledCellLabelledCellAdhesionEnergyParameter(labelled_labelled_adhesion[regime_index]);
                    p_force->SetNagaiHondaCellBoundaryAdhesionEnergyParameter(cell_boundary_adhesion[regime_index]);
                    p_force->SetNagaiHondaLabelledCellBoundaryAdhesionEnergyParameter(labelled_boundary_adhesion[regime_index]);
                    simulator.AddForce(p_force);

                    // Add some noise to avoid local minimum
                    MAKE_PTR(RandomMotionForce<2>, p_random_force);
                    p_random_force->SetMovementParameter(M_CELL_FLUCTUATION);
                    simulator.AddForce(p_random_force);

                    if (M_TIME_TO_STEADY_STATE > 0)
                    {
                        simulator.SetEndTime(M_TIME_TO_STEADY_STATE);
                        // Run simulation
                        simulator.Solve();
                    }

                    // Now label some cells according to the chosen geometry
                    boost::shared_ptr<AbstractCellProperty> p_state(CellPropertyRegistry::Instance()->Get<CellLabel>());
                    if (pattern.compare("Block")==0)
                    {
                        BlockLabelCells(simulator.rGetCellPopulation(), p_state, num_cells_across);
                    }
                    else
                    {
                        RandomlyLabelCells(simulator.rGetCellPopulation().rGetCells(), p_state, 0.5);
                    }

                    // Adjust parameters
                    p_random_force->SetMovementParameter(M_CELL_FLUCTUATION);

                    // Output the simulation info before running
                    std::cout << "Running simulation: regime = " << regime
                              << ", pattern = " << pattern
                              << ", cells across = " << num_cells_across
                              << " (" << num_cells_across*num_cells_across << " cells)" << std::endl;

                    // Run simulation
                    simulator.SetEndTime(M_TIME_TO_STEADY_STATE + M_TIME_FOR_SIMULATION);
                    simulator.Solve();

                    // Check that the same number of cells
                    TS_ASSERT_EQUALS(simulator.rGetCellPopulation().GetNumRealCells(), num_cells_across*num_cells_across);

                    // Test no births or deaths
                    TS_ASSERT_EQUALS(simulator.GetNumBirths(), 0u);
                    TS_ASSERT_EQUALS(simulator.GetNumDeaths(), 0u);

                    // Reset for next run
                    SimulationTime::Instance()->Destroy();
                    SimulationTime::Instance()->SetStartTime(0.0);
                }
            }
        }
    }
};

#endif /* TESTCELLSORTING_HPP_ */
