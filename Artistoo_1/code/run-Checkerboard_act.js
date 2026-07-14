
let CPM = require("./artistoo-cjs-v1.2.0.js")
let {CentroidsWithTorusCorrection, Centroids} = CPM

let config = {
	field_size: [250,250],
	torus: [true,true],
	conf: {
		T: 100,
		J: [[0,30,30],[30,20,10], [30, 10, 20]],
		V: [0,200, 200],
		LAMBDA_V: [0,1, 1],
		P: [0,220, 220],
		LAMBDA_P: [0,2, 2],
    	LAMBDA_ACT : [0,100,100],
    	MAX_ACT : [0,10,10],
    	ACT_MEAN : "geometric"
	},
	simsettings: {
		NRCELLS: [5, 5],
		BURNIN : 10,
		RUNTIME : 5000,
		
		CANVASCOLOR: "EEEEEE",
		CELLCOLOR: ["ff", "0000ff"] ,
   		SHOWBORDERS : [true, true],
   		BORDERCOL : ["ffffff", "ffffff"],
		ACTCOLOR: [true,true],
		zoom : 2,							
		SAVEIMG : true,					
		IMGFRAMERATE : 100,					
		SAVEPATH : "img",				
		EXPNAME : "Checkerboard",	
		
		STATSOUT : { browser: false, node: true }, // Should stats be computed?
		LOGRATE : 100							// Output stats every <LOGRATE> MCS.

	}
}
/*	---------------------------------- */

let custommethods = {
	initializeGrid : initializeGrid,
	logStats : logStats
 }
let sim = new CPM.Simulation( config, custommethods )

function initializeGrid(){
	
	this.addGridManipulator() 
	this.gm.seedCellsInCircle( 1, 50, this.C.midpoint, 70 )
	this.gm.seedCellsInCircle( 2, 50, this.C.midpoint, 70 )

}


function logStats(){
		
		let allcentroids  = this.C.getStat( CPM.CentroidsWithTorusCorrection )

		for( let cid of this.C.cellIDs() ){
		
			// roughly cell diameter = 1
			let thecentroid = allcentroids[cid].map( x => x / 16 )
			
			console.log( "0," , this.time + "," + cid + "," + 
				this.C.cellKind(cid) + "," + thecentroid.join(",") )
			
		}
 
	}

console.log( 'simID' + ",time," + "cellID" + "," + 
				"cellType" + "," + "x,y" )

sim.run()
