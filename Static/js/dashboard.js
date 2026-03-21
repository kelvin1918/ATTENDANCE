/* CLOCK */

setInterval(function(){

let now = new Date()

document.getElementById("time").innerText =
now.toLocaleTimeString()

document.getElementById("date").innerText =
now.toDateString()

},1000)



/* CHART */

const ctx = document.getElementById('absenceChart');

new Chart(ctx,{

type:'bar',

data:{

labels:['John','Anna','Mark','Claire'],

datasets:[{

label:'Absences',

data:[3,5,2,6],

backgroundColor:'#D32F2F'

}]

},

options:{

indexAxis:'y'

}

})



/* CREATE CLASS */

function createClass(){

let subject = document.getElementById("subject").value
let section = document.getElementById("section").value

fetch("/create_class",{

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({
subject:subject,
section:section
})

})
.then(res=>res.json())
.then(data=>{
location.reload()
})

}



/* FLOATING MENU */

function openMenu(x,y){

let menu=document.getElementById("floatingMenu")

menu.style.display="block"
menu.style.left=x+"px"
menu.style.top=y+"px"

}

    