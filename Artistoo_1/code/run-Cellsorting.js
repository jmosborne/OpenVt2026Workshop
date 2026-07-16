
let CPM = require("./artistoo-cjs-v1.2.0.js")
let {CentroidsWithTorusCorrection, Centroids} = CPM

let config = {
	field_size: [150,150],
	torus: [true,true],
	conf: {
		T: 5,
		J: [
			[0,16,16],
			[16,14,11], 
			[16,11,2]],
		V: [0,36, 36],
		LAMBDA_V: [0,1, 1]
	},
	simsettings: {
		NRCELLS: [1,1],
		BURNIN : 0,
		RUNTIME : 1000,
		CANVASCOLOR: "EEEEEE",
		CELLCOLOR: ["ff0000", "0000ff"] ,
   		SHOWBORDERS : [true, true],
   		BORDERCOL : ["ffffff", "ffffff"],
		zoom : 2,							
		SAVEIMG : true,					
		IMGFRAMERATE : 10,					
		SAVEPATH : "img",				
		EXPNAME : "CellSorting2",	
		
		STATSOUT : { browser: false, node: true }, // Should stats be computed?
		LOGRATE : 1							// Output stats every <LOGRATE> MCS.

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
	let gm = this.gm

	for( let xi = 0; xi < 10; xi++ ){
		for( let yi = 0; yi < 10; yi++ ){
			let kind = 1 + ((xi + yi) % 2 ) // checkerboard
			let rect = gm.makeBox( [45+6*xi,45+6*yi], [6,6]  )
			gm.assignCellPixels( rect, kind )
		}
	}
}


function logStats( add = 1 ){

		if( (this.time + add ) % 10 != 0 ) return
		
		
		
		let allcentroids  = this.C.getStat( CPM.CentroidsWithTorusCorrection )

		for( let cid of this.C.cellIDs() ){
		
			// roughly cell diameter = 1
			let thecentroid = allcentroids[cid].map( x => x / 6 )
			
			console.log( "0," , (this.time + add )+ "," + cid + "," + 
				this.C.cellKind(cid) + "," + thecentroid.join(",") )
			
		}
 
	}

console.log( 'simID' + ",time," + "cellID" + "," + 
				"cellType" + "," + "x,y" )

sim.logStats( 0 ) // temporary fix for time counter in artistoo.
sim.run()
