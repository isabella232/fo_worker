
rm(list=ls())

library(gdata)
library(data.table)
library(sqldf)
library(tidyr)

setwd("C:\\Users\\alison.stern\\Documents\\Kohls\\FO Enhancements\\R Code\\R Functions_09.13.2016\\Data Merging")

mydir<-("C:\\Users\\alison.stern\\Documents\\Kohls\\FO Enhancements\\R Code\\R Functions_09.13.2016\\Data Merging")


#------Historical Performance-------------

Hist_perf<-read.csv("Sales Data-WATH-ALLSTR.csv",header = F,sep=",") #Reading python input file of Historical performance 

HSCI<-read.csv("Space Data-WATH-ALLSTR.csv",header = F,sep=",") #Reading python input file of Historical space and climate information

#Future_Space_Entry_Data <-read.csv("Future Space Data-WATH-ALLSTR.csv",header=TRUE,sep=",",check.names=FALSE)
Future_Space_Entry_Data<-NULL
Brand_Exit<-read.csv("Exit Data-WATH-ALLSTR.csv",header = F,sep=",") #Reading python input file of Exit data
#Brand_Exit<-NULL
type="Tiered"

Data_merge<-function(Hist_perf,HSCI,Future_Space_Entry_Data,Brand_Exit,type){

colnames(Hist_perf)=as.character(unlist(Hist_perf[2,])) #Assigning columns names

Hist_perf=Hist_perf[-2,] #Removing column names row

Hist_perf1<-t(Hist_perf) # Transporting the data

colnames(Hist_perf1)<-Hist_perf1[1,] #Assigning column names

Hist_perf1<-Hist_perf1[-1,] #Removing column names row

Hist_perf1<-as.data.frame(Hist_perf1) # Converting into data frame

Hist_perf1<-rename.vars(Hist_perf1,from=c("Store"), to=c("Cat")) # Renaming variables

# Created a function to fill blanks with above cell value
fillTheBlanks <- function(x, missing=""){
  rle <- rle(as.character(x))
  empty <- which(rle$value==missing)
  rle$values[empty] <- rle$value[empty-1] 
  inverse.rle(rle)
}

Hist_perf1$Cat<-fillTheBlanks(Hist_perf1$Cat) #Filling the blank rows with above cell
Hist_perf1<-setDT(Hist_perf1, keep.rownames = TRUE)[] #Creating rowindex as column in data frame
Hist_perf1<-melt(Hist_perf1,measure.vars = colnames(Hist_perf1)[-(1:2)]) #Reshaping the data
trim <- function (x) gsub("^\\s+|\\s+$", "", x) # created function for removing leading and trailing spaces
Hist_perf1$rn<-trim(Hist_perf1$rn)
Hist_perf1<-dcast(Hist_perf1,Cat+variable~rn,value.var = "value") #long to wide format
Hist_perf1<-rename.vars(Hist_perf1,from=c("variable"),to=c("Store")) #Renaming variables
Hist_perf1$Cat<-trim(Hist_perf1$Cat)
#Hist_perf1<-data.frame(Hist_perf1)
#---------Historical space and Climate information--------------

colnames(HSCI)=trim(as.character(unlist(HSCI[1,]))) #Assigning columns names
HSCI1<-HSCI[-1,] #removing not required row
HSCI1<-HSCI1[-1,] #removing not required row
HSCI1<-melt(HSCI1,measure.vars = colnames(HSCI1)[-(1:3)]) #Reshaping the data
HSCI1<-rename.vars(HSCI1,from=c("variable"),to=c("Cat")) #Renaming variables
#HSCI1<-data.frame(HSCI1)

# Merging between Historical performance input and Historical space and climate info
Hist_perf_space<-sqldf("select a.*,b.Climate,b.VSG,b.value as space from Hist_perf1 a left join HSCI1 b on a.Store=b.Store and a.Cat=b.Cat")
Hist_perf_space<-rename.vars(Hist_perf_space,from = c("Cat","space","Sales $","Sales Units","Profit $"), to=c("Category","Space","Sales","Units","Profit"))
big_master_data<-Hist_perf_space[c("Store","Climate","VSG","Category","Space","Sales","Units","Profit","BOH $","BOH Units","CC Count w/ BOH","Profit %","Receipts  $","Receipts Units")]

#Checking for the availability of other required files
# a)Brand Entry file
if(type=="Tiered"){
  # Whether or not user wants to upload future BA space - if not, target BA space is the same as historical BA space 
  if(is.null(Future_Space_Entry_Data)==TRUE){
    Future_Space_Entry_Data<-big_master_data
    for(s in (1:nrow(Future_Space_Entry_Data))){
      Future_Space_Entry_Data$Future_Space[s]<-sum(as.numeric(Future_Space_Entry_Data$Space[which(Future_Space_Entry_Data$Store %in% Future_Space_Entry_Data$Store[s])]))
    }
    Future_Space_Entry_Data<-Future_Space_Entry_Data[!duplicated(Future_Space_Entry_Data[c("Store", "Future_Space")]),]
    Future_Space_Entry_Data<-Future_Space_Entry_Data[c("Store","Future_Space")]
    Future_Space_Entry_Data$Entry_Space<-0
    Future_Space_Entry_Data$VSG<-NA
    Future_Space_Entry_Data$Climate<-NA
    Future_Space_Entry_Data<-Future_Space_Entry_Data[c("Store","Climate","VSG","Future_Space","Entry_Space")]
  } else {
    Future_Space_Entry_Data<-Future_Space_Entry_Data[-1,]
    names(Future_Space_Entry_Data)<-gsub(" ","_",names(Future_Space_Entry_Data))
  }
  #Whether or not user has any brand exit information - if not, there will not be any product/stores with LB/UB = 0 due to brand exit
  if(is.null(Brand_Exit)==TRUE){
    Brand_Exit<-big_master_data
    Brand_Exit$Exit_Flag<-0
    Brand_Exit<-Brand_Exit[c("Store","Category","Exit_Flag")]
    Brand_Exit<-Brand_Exit[!duplicated(Brand_Exit[c("Store", "Category")]),]

  } else{
    colnames(Brand_Exit)=trim(as.character(unlist(Brand_Exit[1,]))) #Assigning columns names
    Brand_Exit<-Brand_Exit[-1,] #removing not required row
    Brand_Exit<-Brand_Exit[-1,]
    Brand_Exit<-gather(Brand_Exit,Category,Store)
    if(is.na(Brand_Exit[2,1])==TRUE){
    Brand_Exit<-big_master_data
    Brand_Exit$Exit_Flag<-0
    Brand_Exit<-Brand_Exit[c("Store","Category","Exit_Flag")]
    Brand_Exit<-Brand_Exit[!duplicated(Brand_Exit[c("Store", "Category")]),]
    } else{
      Brand_Exit<-Brand_Exit[!(Brand_Exit$Store==""),]
      Brand_Exit$Exit_Flag<-"Exit"
    }
  }
} else {
  #target BA space is the same as historical BA space 
  if(is.null(Future_Space_Entry_Data)==TRUE){
    #names(Future_Space_Entry_Data)<-gsub(" ","_",names(Future_Space_Entry_Data))
  Future_Space_Entry_Data<-big_master_data
  for(s in (1:nrow(Future_Space_Entry_Data))){
    Future_Space_Entry_Data$Future_Space[s]<-sum(as.numeric(Future_Space_Entry_Data$Space[which(Future_Space_Entry_Data$Store %in% Future_Space_Entry_Data$Store[s])]))
  }
  Future_Space_Entry_Data<-Future_Space_Entry_Data[!duplicated(Future_Space_Entry_Data[c("Store", "Future_Space")]),]
  Future_Space_Entry_Data<-Future_Space_Entry_Data[c("Store","Future_Space")]
  Future_Space_Entry_Data$Entry_Space<-0
  Future_Space_Entry_Data$VSG<-NA
  Future_Space_Entry_Data$Climate<-NA
  Future_Space_Entry_Data<-Future_Space_Entry_Data[c("Store","Climate","VSG","Future_Space","Entry_Space")]
  } else {
    names(Future_Space_Entry_Data)<-gsub(" ","_",names(Future_Space_Entry_Data))
    Future_Space_Entry_Data<-Future_Space_Entry_Data[-1,]
    Future_Space_Entry_Data$Entry_Space<-0
  }
  #there will not be any product/stores with LB/UB = 0 due to brand exit
  Brand_Exit<-big_master_data
  Brand_Exit$Exit_Flag<-0
  Brand_Exit<-Brand_Exit[c("Store","Category","Exit_Flag")]
  Brand_Exit<-Brand_Exit[!duplicated(Brand_Exit[c("Store", "Category")]),]
}

big_master_data<-merge(big_master_data,Brand_Exit,by=c("Store","Category"),all.x=TRUE)
big_master_data$Exit_Flag<-ifelse(is.na(big_master_data$Exit_Flag)==TRUE,0,big_master_data$Exit_Flag)
big_master_data<-merge(big_master_data,Future_Space_Entry_Data[,which(names(Future_Space_Entry_Data) %in% c("Store","Future_Space","Entry_Space"))],by="Store",all.x=TRUE)
big_master_data<-big_master_data[c("Store","Climate","VSG","Category","Space","Sales","Units","Profit","Exit_Flag","Future_Space","Entry_Space","BOH $","BOH Units","CC Count w/ BOH","Profit %","Receipts  $","Receipts Units")]

return(big_master_data)

}

output<-Data_merge(Hist_perf,HSCI,Future_Space_Entry_Data,Brand_Exit,type)
write.csv(output,"output.csv",row.names = FALSE)
