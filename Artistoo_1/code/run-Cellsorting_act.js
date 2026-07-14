
let CPM = require("./artistoo-cjs-v1.2.0.js")
let {CentroidsWithTorusCorrection, Centroids} = CPM

let config = {
	field_size: [250,250],
	torus: [true,true],
	conf: {
		T: 100,
		J: [[0,40,40],[40,12,30], [40, 30, 12]],
		V: [0,200, 200],
		LAMBDA_V: [0,1, 1],
		P: [0,220, 220],
		LAMBDA_P: [0,2, 2],
    	LAMBDA_ACT : [0,200,200],
    	MAX_ACT : [0,10,10],
    	ACT_MEAN : "geometric"
	},
	simsettings: {
		NRCELLS: [5, 5],
		BURNIN : 10,
		RUNTIME : 15000,
		
		CANVASCOLOR: "EEEEEE",
		CELLCOLOR: ["ff", "0000ff"] ,
   		SHOWBORDERS : [true, true],
   		BORDERCOL : ["ffffff", "ffffff"],
		ACTCOLOR: [true,true],
		zoom : 2,							
		SAVEIMG : true,					
		IMGFRAMERATE : 100,					
		SAVEPATH : "img",				
		EXPNAME : "CellSorting",	
		
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
	// don't initialize with lambda_act due to artifacts from high expansion force + feedback
	const lact1 = this.C.conf.LAMBDA_ACT[1]
	const lact2 = this.C.conf.LAMBDA_ACT[2]
	this.C.conf.LAMBDA_ACT[1] = 0
	this.C.conf.LAMBDA_ACT[2] = 0
	this.gm.seedCellsInCircle( 1, 100, this.C.midpoint, 70 )
	for( let cid of this.C.cellIDs() ){
		if( this.C.random() < 0.5 ) this.C.setCellKind( cid, 2 )
	}
	
	for( let t= 0; t < 10 ; t++ ){
		this.C.timeStep()
	}
	// reset to original value
	this.C.conf.LAMBDA_ACT[1] = lact1
	this.C.conf.LAMBDA_ACT[2] = lact2

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
