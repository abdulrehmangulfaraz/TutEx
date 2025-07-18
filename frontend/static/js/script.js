// Define premium subjects
const premiumSubjects = ["Mathematics", "Physics", "Chemistry", "Biology", "Audit"];

// Define area base fees
const areaBaseFees = {
  "DHA": 5000,
  "Gulshan-e-Iqbal": 4000,
  "PECHS": 4000,
  "Saddar": 4000
};

// Define board additional fees
const boardAdditionalFees = {
  "Cambridge O'Levels": 4000,
  "Cambridge A'Levels": 4000,
  "ACCA": 4000,
  "ICAP": 4000
};

function calculateFee() {
  // Get selected area and board
  const selectedArea = document.getElementById('area').value;
  const selectedBoard = document.getElementById('board').value;
  
  // Calculate base fees
  let areaFee = 2000; // Default for other areas
  if (areaBaseFees[selectedArea]) {
    areaFee = areaBaseFees[selectedArea];
  }
  
  let boardFee = 2000; // Default for other boards
  if (boardAdditionalFees[selectedBoard]) {
    boardFee = boardAdditionalFees[selectedBoard];
  }
  
  // Calculate per subject cap
  const perSubjectCap = areaFee + boardFee;
  
  // Calculate total fee
  let totalFee = areaFee + boardFee; // Start with base fees
  
  // Add subject fees
  const selectedSubjects = document.querySelectorAll('input[name="subjects"]:checked');
  selectedSubjects.forEach(subject => {
    const subjectName = subject.value.split(' - ')[0]; // Get subject name without code
    let subjectFee = 5000; // Default for other subjects
    
    if (premiumSubjects.includes(subjectName)) {
      subjectFee = 6000;
    }
    
    // Apply cap per subject
    if (subjectFee > perSubjectCap) {
      subjectFee = perSubjectCap;
    }
    
    totalFee += subjectFee;
  });
  
  document.getElementById('totalFee').textContent = totalFee;
}



// Update the rest of the code to use this calculateFee function