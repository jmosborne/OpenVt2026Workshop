let CPM = require("../../build/artistoo-cjs.js")
let {CentroidsWithTorusCorrection, Centroids} = CPM

/*	----------------------------------
	CONFIGURATION SETTINGS
	----------------------------------
*/
let config = {
	"field_size": [300,300],
	"torus": [true,true],
	"conf": {
		"T": 100,
		"J": [[0,50,50],[50,10,50], [50, 50, 10]],
		"V": [0,500, 500],
		"LAMBDA_V": [0,50, 50],
		"P": [0,320, 320],
		"LAMBDA_P": [0,2, 2],
    "LAMBDA_ACT" : [0,100,200],
    "MAX_ACT" : [0,30,30],
    "ACT_MEAN" : "geometric"
	},
	"simsettings": {
		"zoom": 1,
		"CANVASCOLOR": "EEEEEE",
		"NRCELLS": [5, 5],
		"CELLCOLOR": ["ff", "0000ff"] ,
    SHOWBORDERS : [true, true],
    "BORDERCOL" : ["ffffff", "ffffff"],
		"ACTCOLOR": [true,true]
	},


	
	// Simulation setup and configuration
	simsettings : {
	
		// Cells on the grid
		NRCELLS : [1,1],					// Number of cells to seed for all
		// non-background cellkinds.
	
		// Runtime etc
		BURNIN : 500,
		RUNTIME : 1000,
		RUNTIME_BROWSER : 20000,
		
		// Visualization
		CANVASCOLOR : "eaecef",
		CELLCOLOR : ["000000","FF0000"],
		ACTCOLOR : [true,false],			// Should pixel activity values be displayed?
		SHOWBORDERS : [true,true],				// Should cellborders be displayed?
		zoom : 2,							// zoom in on canvas with this factor.
		
		// Output images
		SAVEIMG : true,					// Should a png image of the grid be saved
		// during the simulation?
		IMGFRAMERATE : 1,					// If so, do this every <IMGFRAMERATE> MCS.
		SAVEPATH : "output/img/CellSorting",				// ... And save the image in this folder.
		EXPNAME : "CellSorting",					// Used for the filename of output images.
		
		// Output stats etc
		STATSOUT : { browser: false, node: true }, // Should stats be computed?
		LOGRATE : 10							// Output stats every <LOGRATE> MCS.

	}
}
/*	---------------------------------- */


	 /* 	The following functions are defined below and will be added to
	 	the simulation object.*/
	 let custommethods = {
	 	initializeGrid : initializeGrid,
		logStats : logStats
	 }
	let sim = new CPM.Simulation( config, custommethods )





/* The following custom methods will be added to the simulation object
below. */
function initializeGrid(){
	
	// add the GridManipulator if not already there and if you need it
	if( !this.helpClasses["gm"] ){ this.addGridManipulator() }
	
	this.gm.seedCellsInCircle( 1, 500, this.C.midpoint, this.C.extents[0]/3 )
	this.gm.seedCellsInCircle( 2, 500, this.C.midpoint, this.C.extents[0]/3 )

}


function logStats(){
		
		// compute centroids for all cells
		let allcentroids 
		let torus = false
		for( let d = 0; d < this.C.grid.ndim; d++ ){
			if( this.C.grid.torus[d] ){
				torus = true
			}
		}
		if( torus ){
			allcentroids = this.C.getStat( CentroidsWithTorusCorrection )
		} else {
			allcentroids = this.C.getStat( Centroids )
		} 
		

		for( let cid of this.C.cellIDs() ){
		
			let thecentroid = allcentroids[cid]
			
			// eslint-disable-next-line no-console
			console.log( "0," , this.time + "," + cid + "," + 
				this.C.cellKind(cid) + "," + thecentroid.join(",") )
			
		}
 
	}

console.log( 'simID' + ",time," + "CellID" + "," + 
				"CellKind" + "," + "x,y" )

sim.run()
